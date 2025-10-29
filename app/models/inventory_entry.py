from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..database import Base


class EntryType(str, enum.Enum):
    PRODUCTION = "production"           # Producción interna
    PURCHASE = "purchase"               # Compra a proveedores
    RETURN = "return"                   # Devolución de clientes
    ADJUSTMENT = "adjustment"           # Ajuste de inventario
    TRANSFER = "transfer"               # Transferencia entre bodegas
    INITIAL = "initial"                 # Inventario inicial


class EntryStatus(str, enum.Enum):
    DRAFT = "draft"                     # Borrador
    PENDING = "pending"                 # Pendiente de aprobación
    APPROVED = "approved"               # Aprobado
    COMPLETED = "completed"             # Completado (stock actualizado)
    CANCELLED = "cancelled"             # Cancelado


class InventoryEntry(Base):
    __tablename__ = "inventory_entries"

    id = Column(Integer, primary_key=True, index=True)
    entry_number = Column(String, unique=True, index=True, nullable=False)

    # Entry details
    entry_type = Column(Enum(EntryType), nullable=False)
    status = Column(Enum(EntryStatus), default=EntryStatus.DRAFT)

    # References
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False)  # Usuario que registra
    # Info del proveedor (opcional)
    supplier_info = Column(String, nullable=True)

    # Financial
    total_cost = Column(Float, default=0.0)  # Costo total de la entrada

    # Dates
    entry_date = Column(DateTime(timezone=True), server_default=func.now())
    expected_date = Column(
        DateTime(
            timezone=True),
        nullable=True)  # Fecha esperada
    completed_date = Column(
        DateTime(
            timezone=True),
        nullable=True)  # Fecha completada

    # Additional info
    notes = Column(Text)
    # Número de factura, orden de compra, etc.
    reference_document = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="inventory_entries")
    items = relationship(
        "InventoryEntryItem",
        back_populates="entry",
        cascade="all, delete-orphan")


class InventoryEntryItem(Base):
    __tablename__ = "inventory_entry_items"

    id = Column(Integer, primary_key=True, index=True)
    entry_id = Column(
        Integer,
        ForeignKey("inventory_entries.id"),
        nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    # Quantities
    quantity = Column(Numeric(10, 2), nullable=False)  # 10 dígitos totales, 2 decimales
    unit_cost = Column(Float, default=0.0)  # Costo por unidad
    # Costo total (quantity * unit_cost)
    total_cost = Column(Float, default=0.0)

    # Additional info
    batch_number = Column(String, nullable=True)  # Número de lote
    expiry_date = Column(DateTime(timezone=True),
                         nullable=True)  # Fecha de vencimiento
    notes = Column(Text)

    # Relationships
    entry = relationship("InventoryEntry", back_populates="items")
    product = relationship("Product")
