from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
import uuid
from ..database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    nombre = Column(String, nullable=False)
    subdominio = Column(String, unique=True, index=True, nullable=False)
    schema_name = Column(String, unique=True, index=True, nullable=False)
    active = Column(Boolean, nullable=False, default=True, server_default="true")
    is_trial = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def generate_schema_name(self) -> str:
        """Genera el nombre del schema concatenando nombre y token sin espacios (para uso inicial)"""
        clean_name = self.nombre.replace(" ", "").lower()
        return f"{clean_name}_{self.token.lower()}"
