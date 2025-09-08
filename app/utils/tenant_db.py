"""
Utilidades para manejo de base de datos multitenant
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from alembic.config import Config
from alembic.script import ScriptDirectory
import os
import logging
from typing import Optional
from ..config import settings

logger = logging.getLogger(__name__)


def get_engine_for_schema(schema_name: str):
    """
    Crea un engine de SQLAlchemy configurado para un schema específico
    """
    # Crear URL con search_path específico para el schema
    db_url = f"{settings.DATABASE_URL}?options=-csearch_path%3D{schema_name}"
    return create_engine(db_url)


def get_session_for_schema(schema_name: str):
    """
    Crea una sesión de SQLAlchemy para un schema específico
    """
    engine = get_engine_for_schema(schema_name)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


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
            # Cambiar al schema específico
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
