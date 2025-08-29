from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime, date
from ..models.invoice import InvoiceStatus, PaymentMethod


class InvoiceBase(BaseModel):
    order_id: int
    payment_method: Optional[PaymentMethod] = None
    tax_rate: float = Field(default=0.12, ge=0, le=1, description="Tax rate (0.12 = 12%)")
    discount_amount: float = Field(default=0.0, ge=0, description="Discount amount")
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    payment_terms: str = Field(default="Pago contra entrega", max_length=255)


class InvoiceCreate(InvoiceBase):
    pass


class InvoiceUpdate(BaseModel):
    status: Optional[InvoiceStatus] = None
    payment_method: Optional[PaymentMethod] = None
    discount_amount: Optional[float] = Field(None, ge=0)
    due_date: Optional[datetime] = None
    notes: Optional[str] = None
    payment_terms: Optional[str] = Field(None, max_length=255)
    paid_amount: Optional[float] = Field(None, ge=0)
    paid_date: Optional[datetime] = None

    @validator('paid_amount')
    def validate_paid_amount(cls, v):
        if v is not None and v < 0:
            raise ValueError('Paid amount cannot be negative')
        return v


class InvoiceResponse(InvoiceBase):
    id: int
    invoice_number: str
    status: InvoiceStatus
    
    # Financial information
    subtotal: float
    tax_amount: float
    total_amount: float
    paid_amount: float
    balance_due: float
    
    # Dates
    issue_date: datetime
    paid_date: Optional[datetime] = None
    
    # PDF tracking
    pdf_generated: bool
    pdf_path: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InvoiceListResponse(BaseModel):
    id: int
    invoice_number: str
    order_id: int
    status: InvoiceStatus
    total_amount: float
    balance_due: float
    issue_date: datetime
    due_date: Optional[datetime] = None
    client_name: Optional[str] = None  # Will be populated from order relationship

    class Config:
        from_attributes = True


class InvoiceSummary(BaseModel):
    """Summary for dashboard/reports"""
    total_invoices: int
    total_amount: float
    paid_amount: float
    pending_amount: float
    overdue_count: int
    overdue_amount: float


class PaymentCreate(BaseModel):
    """For recording payments against invoices"""
    invoice_id: int
    amount: float = Field(..., gt=0, description="Payment amount must be positive")
    payment_method: PaymentMethod
    payment_date: Optional[datetime] = None
    notes: Optional[str] = None

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Payment amount must be greater than 0')
        return v


class InvoicePDFRequest(BaseModel):
    """Request schema for PDF generation"""
    invoice_id: int
    regenerate: bool = Field(default=False, description="Force regenerate PDF even if exists")


class CompanyInfo(BaseModel):
    """Company information for invoice header"""
    name: str = "Smart Orders"
    address: str = "Ciudad de Guatemala, Guatemala"
    phone: str = "+502 2222-3333"
    email: str = "contacto@smartorders.gt"
    nit: str = "12345678-9"
    logo_path: Optional[str] = None
