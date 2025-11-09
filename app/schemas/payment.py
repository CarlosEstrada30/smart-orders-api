from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from ..models.payment import PaymentStatus, OrderPaymentStatus
from ..models.invoice import PaymentMethod  # Reuse PaymentMethod from Invoice
from .base import TimezoneAwareBaseModel, create_timezone_aware_datetime_field


class PaymentBase(BaseModel):
    order_id: int
    amount: float = Field(..., gt=0, description="Amount must be greater than 0")
    payment_method: PaymentMethod
    notes: Optional[str] = None

    @validator('amount')
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return round(v, 2)  # Redondear a 2 decimales


class PaymentCreate(PaymentBase):
    pass


class PaymentResponse(PaymentBase, TimezoneAwareBaseModel):
    id: int
    payment_number: str
    status: PaymentStatus
    payment_date: datetime = create_timezone_aware_datetime_field(
        description="Fecha del pago (en zona horaria del cliente)"
    )
    created_by_user_id: Optional[int] = None
    created_at: datetime = create_timezone_aware_datetime_field(
        description="Fecha y hora de creación (en zona horaria del cliente)"
    )
    updated_at: Optional[datetime] = create_timezone_aware_datetime_field(
        default=None,
        description="Fecha y hora de última actualización (en zona horaria del cliente)"
    )

    class Config:
        from_attributes = True


class PaymentSummary(BaseModel):
    """Resumen de pagos de una orden"""
    total_paid: float
    total_balance_due: float
    payment_count: int
    payments: List[PaymentResponse] = []

    class Config:
        from_attributes = True


class OrderPaymentSummary(BaseModel):
    """Resumen completo de pagos de una orden"""
    order_id: int
    order_number: str
    total_amount: float
    paid_amount: float
    balance_due: float
    payment_status: OrderPaymentStatus
    payment_count: int
    payments: List[PaymentResponse] = []

    class Config:
        from_attributes = True

