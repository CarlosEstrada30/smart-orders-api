from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..database import Base


class UserRole(str, enum.Enum):
    EMPLOYEE = "EMPLOYEE"     # Empleado básico (almacén/producción)
    SALES = "SALES"          # Vendedor
    DRIVER = "DRIVER"        # Repartidor/Conductor
    SUPERVISOR = "SUPERVISOR"  # Supervisor
    MANAGER = "MANAGER"       # Gerente/Dueño
    ADMIN = "ADMIN"          # Administrador sistema


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    role = Column(Enum(UserRole), default=UserRole.EMPLOYEE, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    inventory_entries = relationship("InventoryEntry", back_populates="user")
