from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.sql import func
from ..database import Base


class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)  # Nombre de la empresa
    business_name = Column(String, nullable=False)  # Razón social
    nit = Column(String, nullable=False)  # NIT de la empresa
    address = Column(Text)  # Dirección de la empresa
    logo_url = Column(String)  # URL del logo almacenado en R2
    phone = Column(String)  # Teléfono de contacto
    email = Column(String)  # Email de contacto
    website = Column(String)  # Sitio web
    is_active = Column(Boolean, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
