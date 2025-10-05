from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@localhost/smart_orders_db"
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Environment configuration
    ENVIRONMENT: str = "development"

    # Database connection settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600  # 1 hour
    DB_CONNECT_TIMEOUT: int = 10

    # SSL Configuration for production
    DB_SSL_MODE: str = "prefer"  # prefer, require, disable
    DB_SSL_CERT: Optional[str] = None
    DB_SSL_KEY: Optional[str] = None
    DB_SSL_ROOT_CERT: Optional[str] = None

    # Cloudflare R2 Configuration
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: Optional[str] = None
    # Se construirá automáticamente si no se proporciona
    R2_ENDPOINT_URL: Optional[str] = None
    # URL pública para acceder a los archivos
    R2_PUBLIC_URL: Optional[str] = None

    # Logging configuration
    LOG_LEVEL: str = "INFO"
    
    # Timezone configuration
    DEFAULT_TIMEZONE: str = "America/Guatemala"  # UTC-6
    TIMEZONE_HEADER: str = "X-Timezone"

    def get_database_url(self) -> str:
        """
        Retorna la URL de la base de datos con parámetros SSL si es necesario
        """
        base_url = self.DATABASE_URL

        # Si estamos en producción y no hay parámetros SSL en la URL
        if (self.ENVIRONMENT == "production" and
                "sslmode" not in base_url and
                self.DB_SSL_MODE != "disable"):

            separator = "&" if "?" in base_url else "?"
            ssl_params = f"sslmode={self.DB_SSL_MODE}"

            if self.DB_SSL_CERT:
                ssl_params += f"&sslcert={self.DB_SSL_CERT}"
            if self.DB_SSL_KEY:
                ssl_params += f"&sslkey={self.DB_SSL_KEY}"
            if self.DB_SSL_ROOT_CERT:
                ssl_params += f"&sslrootcert={self.DB_SSL_ROOT_CERT}"

            base_url += separator + ssl_params

        return base_url

    @property
    def is_production(self) -> bool:
        """
        Retorna True si estamos en ambiente de producción
        """
        return self.ENVIRONMENT.lower() == "production"

    class Config:
        env_file = ".env"


settings = Settings()
