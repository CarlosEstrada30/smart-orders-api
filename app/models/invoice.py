from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..database import Base


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    CHECK = "check"
    OTHER = "other"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String, unique=True, index=True, nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    
    # Invoice details
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    payment_method = Column(Enum(PaymentMethod), nullable=True)
    
    # Financial information
    subtotal = Column(Float, nullable=False)
    tax_rate = Column(Float, default=0.12)  # 12% IVA Guatemala
    tax_amount = Column(Float, nullable=False)
    discount_amount = Column(Float, default=0.0)
    total_amount = Column(Float, nullable=False)
    
    # Payment tracking
    paid_amount = Column(Float, default=0.0)
    balance_due = Column(Float, nullable=False)
    
    # Dates
    issue_date = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(DateTime(timezone=True), nullable=True)
    paid_date = Column(DateTime(timezone=True), nullable=True)
    
    # Additional information
    notes = Column(Text)
    payment_terms = Column(String, default="Pago contra entrega")
    
    # PDF tracking
    pdf_generated = Column(Boolean, default=False)
    pdf_path = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    order = relationship("Order", back_populates="invoice")


# Agregar la relación inversa en Order
# Esto se agregará al modelo Order existente
