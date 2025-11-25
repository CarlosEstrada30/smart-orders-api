from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..database import Base
from .invoice import PaymentMethod


class PaymentStatus(str, enum.Enum):
    CONFIRMED = "confirmed"       # Pago confirmado (por defecto al crear)
    CANCELLED = "cancelled"       # Pago cancelado


class OrderPaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"           # Sin pagos
    PARTIAL = "partial"          # Pago parcial
    PAID = "paid"               # Pagado completamente


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_number = Column(String, unique=True, index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)

    # Payment details
    amount = Column(Numeric(10, 2), nullable=False)  # Monto del pago
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(PaymentStatus, values_callable=lambda x: [e.value for e in x]), default=PaymentStatus.CONFIRMED)

    # Payment tracking
    payment_date = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text, nullable=True)  # Notas opcionales

    # User tracking (auditoría)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    order = relationship("Order", back_populates="payments")
    created_by = relationship("User")
