"""
Utilidades para manejo de base de datos multitenant
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool
from alembic.config import Config
from alembic.script import ScriptDirectory
import os
import logging
from typing import Optional
from ..config import settings

logger = logging.getLogger(__name__)


def get_engine_config_for_tenant():
    """
    Retorna la configuración del engine para conexiones de tenant usando settings
    """
    config = {
        "pool_size": max(2, settings.DB_POOL_SIZE // 2),  # Pool más pequeño para tenants
        "max_overflow": max(3, settings.DB_MAX_OVERFLOW // 2),
        "pool_pre_ping": True,   # Verificar conexiones antes de usarlas
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "connect_args": {
            "connect_timeout": settings.DB_CONNECT_TIMEOUT,
            "application_name": "smart-orders-api-tenant"
        }
    }

    # Configuraciones específicas para producción (Render)
    if settings.is_production:
        config["connect_args"].update({
            "sslmode": settings.DB_SSL_MODE if settings.DB_SSL_MODE != "prefer" else "require",
        })

        # Agregar certificados SSL si están configurados
        if settings.DB_SSL_CERT:
            config["connect_args"]["sslcert"] = settings.DB_SSL_CERT
        if settings.DB_SSL_KEY:
            config["connect_args"]["sslkey"] = settings.DB_SSL_KEY
        if settings.DB_SSL_ROOT_CERT:
            config["connect_args"]["sslrootcert"] = settings.DB_SSL_ROOT_CERT

        # Pool aún más conservador para tenants en producción
        config["pool_size"] = min(2, config["pool_size"])
        config["max_overflow"] = min(3, config["max_overflow"])
        config["pool_recycle"] = min(1800, settings.DB_POOL_RECYCLE)
    else:
        # Pool ultra conservador para desarrollo local con tenants
        config["pool_size"] = 1  # Solo 1 conexión por schema en desarrollo
        config["max_overflow"] = 2  # Máximo 2 overflow

    return config


def get_engine_for_schema(schema_name: str):
    """
    Crea un engine de SQLAlchemy configurado para un schema específico
    """
    # Agregar comillas dobles si el schema tiene caracteres especiales
    # y encodificar correctamente para URL (%22 en lugar de ")
    if any(c in schema_name for c in ['-', ' ', '.', '+']):
        quoted_schema = f'%22{schema_name}%22'
    else:
        quoted_schema = schema_name

    # Crear URL con search_path específico para el schema
    base_url = settings.get_database_url()
    # Determinar el separador correcto para parámetros adicionales
    separator = "&" if "?" in base_url else "?"
    db_url = f"{base_url}{separator}options=-csearch_path%3D{quoted_schema}"

    # Aplicar configuración específica para tenant
    engine_config = get_engine_config_for_tenant()

    return create_engine(
        db_url,
        **engine_config,
        poolclass=QueuePool,
        echo=False
    )


def get_session_for_schema(schema_name: str):
    """
    Crea una sesión de SQLAlchemy para un schema específico
    Con manejo de reintentos para mayor robustez
    """
    from sqlalchemy.exc import OperationalError, DisconnectionError
    import time
    import logging

    logger = logging.getLogger(__name__)

    max_retries = 3
    retry_delay = 1  # segundos

    for attempt in range(max_retries):
        try:
            engine = get_engine_for_schema(schema_name)
            SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            session = SessionLocal()

            # Verificar que la conexión funciona
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
            return session

        except (OperationalError, DisconnectionError) as e:
            if attempt == max_retries - 1:
                logger.error(f"Error de conexión para schema '{schema_name}' después de {max_retries} intentos: {e}")
                raise
            logger.warning(f"Error de conexión para schema '{schema_name}' (intento {attempt + 1}/{max_retries}): {e}")
            time.sleep(retry_delay)
            retry_delay *= 2  # Backoff exponencial
        except Exception as e:
            logger.error(f"Error inesperado creando sesión para schema '{schema_name}': {e}")
            raise


def create_schema_if_not_exists(schema_name: str) -> bool:
    """
    Crea un schema si no existe

    Returns:
        bool: True si el schema se creó o ya existía, False si hubo error
    """
    try:
        # Usar el engine por defecto (conectado al schema public)
        from ..database import engine

        with engine.connect() as connection:
            # Verificar si el schema ya existe
            result = connection.execute(text("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.schemata
                    WHERE schema_name = :schema_name
                )
            """), {"schema_name": schema_name})

            exists = result.scalar()

            if not exists:
                # Crear el schema
                connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
                connection.commit()
                logger.info(f"Schema '{schema_name}' creado exitosamente")
            else:
                logger.info(f"Schema '{schema_name}' ya existe")

            return True

    except SQLAlchemyError as e:
        logger.error(f"Error al crear schema '{schema_name}': {str(e)}")
        return False


def run_migrations_for_schema(schema_name: str) -> bool:
    """
    Ejecuta las migraciones de Alembic en un schema específico

    Crea las tablas directamente en el schema usando el metadata existente

    Returns:
        bool: True si las migraciones se ejecutaron exitosamente, False si hubo error
    """
    try:
        from ..database import Base

        # Crear un engine específico para el schema
        engine_for_schema = get_engine_for_schema(schema_name)

        # Crear todas las tablas en el schema
        Base.metadata.create_all(bind=engine_for_schema)

        # Crear la tabla alembic_version para tracking de migraciones
        with engine_for_schema.connect() as connection:
            # Cambiar al schema específico (usar comillas dobles siempre para mayor seguridad)
            connection.execute(
                text(f'SET search_path TO "{schema_name}", public'))

            # Crear tabla de versiones de alembic si no existe
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS alembic_version (
                    version_num VARCHAR(32) NOT NULL,
                    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                )
            """))

            # Marcar como actualizado a la versión actual (head)
            # Obtener la versión actual desde el directorio de scripts
            alembic_cfg = Config(os.path.join(os.getcwd(), "alembic.ini"))
            script_dir = ScriptDirectory.from_config(alembic_cfg)
            head_revision = script_dir.get_current_head()

            if head_revision:
                # Insertar o actualizar la versión
                connection.execute(text("""
                    INSERT INTO alembic_version (version_num) VALUES (:version)
                    ON CONFLICT (version_num) DO NOTHING
                """), {"version": head_revision})

            connection.commit()

        logger.info(
            f"Migraciones ejecutadas exitosamente para schema '{schema_name}'")
        return True

    except Exception as e:
        logger.error(
            f"Error ejecutando migraciones para schema '{schema_name}': {str(e)}")
        return False


def drop_schema_if_exists(schema_name: str) -> bool:
    """
    Elimina un schema si existe (OPERACIÓN DESTRUCTIVA)

    Returns:
        bool: True si el schema se eliminó o no existía, False si hubo error
    """
    try:
        from ..database import engine

        with engine.connect() as connection:
            # Verificar si el schema existe
            result = connection.execute(text("""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.schemata
                    WHERE schema_name = :schema_name
                )
            """), {"schema_name": schema_name})

            exists = result.scalar()

            if exists:
                # Eliminar el schema
                connection.execute(
                    text(f'DROP SCHEMA "{schema_name}" CASCADE'))
                connection.commit()
                logger.info(f"Schema '{schema_name}' eliminado exitosamente")
            else:
                logger.info(f"Schema '{schema_name}' no existe")

            return True

    except SQLAlchemyError as e:
        logger.error(f"Error al eliminar schema '{schema_name}': {str(e)}")
        return False


def get_current_schema(engine) -> Optional[str]:
    """
    Obtiene el schema actual de una conexión
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT current_schema()"))
            return result.scalar()
    except SQLAlchemyError as e:
        logger.error(f"Error obteniendo schema actual: {str(e)}")
        return None


def list_schemas() -> list:
    """
    Lista todos los schemas disponibles en la base de datos
    """
    try:
        from ..database import engine

        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY schema_name
            """))

            return [row[0] for row in result.fetchall()]

    except SQLAlchemyError as e:
        logger.error(f"Error listando schemas: {str(e)}")
        return []
