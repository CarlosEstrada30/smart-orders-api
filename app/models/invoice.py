from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from ..database import Base


class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"                    # Borrador
    FEL_PENDING = "fel_pending"        # Enviando a FEL
    FEL_AUTHORIZED = "fel_authorized"  # Autorizada por SAT
    FEL_REJECTED = "fel_rejected"      # Rechazada por SAT
    ISSUED = "ISSUED"                  # Emitida oficialmente (con FEL)
    PAID = "PAID"                      # Pagada
    OVERDUE = "OVERDUE"                # Vencida
    CANCELLED = "CANCELLED"            # Anulada


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
    
    # FEL (Facturación Electrónica en Línea) - Guatemala
    fel_uuid = Column(String, nullable=True, index=True)               # UUID de SAT
    dte_number = Column(String, nullable=True, index=True)             # Número DTE
    fel_authorization_date = Column(DateTime(timezone=True), nullable=True)
    fel_xml_path = Column(String, nullable=True)                      # XML generado
    fel_certification_date = Column(DateTime(timezone=True), nullable=True)
    fel_certifier = Column(String, nullable=True)                     # Certificador usado (ej: FacturasGT, Digifact)
    fel_series = Column(String, nullable=True)                        # Serie FEL
    fel_number = Column(String, nullable=True)                        # Número FEL
    fel_error_message = Column(Text, nullable=True)                   # Error FEL si aplica
    requires_fel = Column(Boolean, default=True)                      # Si requiere procesamiento FEL
    
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
