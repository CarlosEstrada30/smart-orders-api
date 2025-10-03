from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError, DisconnectionError
import time
import logging
from .config import settings

logger = logging.getLogger(__name__)


# Configuración específica para producción en Render
def get_engine_config():
    """
    Retorna la configuración del engine según el entorno usando settings
    """
    config = {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_pre_ping": True,  # Verificar conexiones antes de usarlas
        "pool_recycle": settings.DB_POOL_RECYCLE,
        "pool_timeout": settings.DB_POOL_TIMEOUT,
        "connect_args": {
            "connect_timeout": settings.DB_CONNECT_TIMEOUT,
            "application_name": "smart-orders-api"
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

        # Pool más conservador para producción
        config["pool_size"] = min(3, settings.DB_POOL_SIZE)
        config["max_overflow"] = min(7, settings.DB_MAX_OVERFLOW)
        config["pool_recycle"] = min(1800, settings.DB_POOL_RECYCLE)  # máximo 30 minutos
    else:
        # Pool más pequeño para desarrollo local para evitar "too many clients"
        config["pool_size"] = min(2, settings.DB_POOL_SIZE)
        config["max_overflow"] = min(3, settings.DB_MAX_OVERFLOW)

    return config


# Crear engine con configuración apropiada
engine_config = get_engine_config()
engine = create_engine(
    settings.get_database_url(),
    **engine_config,
    poolclass=QueuePool,
    echo=not settings.is_production  # Solo debug en desarrollo
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Dependency que proporciona una sesión de base de datos con manejo de reintentos
    """
    max_retries = 3
    retry_delay = 1  # segundos

    db = None
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            # Verificar que la conexión funciona
            db.execute(text("SELECT 1"))
            break
        except (OperationalError, DisconnectionError) as e:
            if db:
                db.close()
                db = None
            if attempt == max_retries - 1:
                logger.error(f"Error de conexión después de {max_retries} intentos: {e}")
                raise
            logger.warning(f"Error de conexión (intento {attempt + 1}/{max_retries}): {e}")
            time.sleep(retry_delay)
            retry_delay *= 2  # Backoff exponencial
        except Exception as e:
            if db:
                db.close()
            logger.error(f"Error inesperado en get_db: {e}")
            raise

    try:
        yield db
    finally:
        if db:
            try:
                db.close()
            except Exception as e:
                logger.warning(f"Error cerrando sesión: {e}")


def get_db_with_retries(max_retries: int = 3, retry_delay: float = 1.0):
    """
    Función auxiliar para obtener una sesión de DB con reintentos personalizados
    """
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            # Verificar que la conexión funciona
            db.execute(text("SELECT 1"))
            return db
        except (OperationalError, DisconnectionError) as e:
            if attempt == max_retries - 1:
                logger.error(f"Error de conexión después de {max_retries} intentos: {e}")
                raise
            logger.warning(f"Error de conexión (intento {attempt + 1}/{max_retries}): {e}")
            time.sleep(retry_delay)
            retry_delay *= 2
        except Exception as e:
            logger.error(f"Error inesperado obteniendo sesión DB: {e}")
            raise
