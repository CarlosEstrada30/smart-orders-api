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


class BulkPaymentCreate(BaseModel):
    """Schema para crear múltiples pagos en un solo request"""
    payments: List[PaymentCreate] = Field(..., min_items=1, description="Lista de pagos a crear")

    @validator('payments')
    def validate_payments(cls, v):
        if not v or len(v) == 0:
            raise ValueError('Debe proporcionar al menos un pago')
        return v


class PaymentError(BaseModel):
    """Información sobre un pago que falló"""
    order_id: int = Field(..., description="ID de la orden que no se pudo procesar")
    order_number: Optional[str] = Field(None, description="Número de la orden (si existe)")
    client_name: Optional[str] = Field(None, description="Nombre del cliente (si la orden existe)")
    amount: float = Field(..., description="Monto del pago que falló")
    payment_method: PaymentMethod = Field(..., description="Método de pago intentado")
    reason: str = Field(..., description="Razón por la cual falló el pago")
    notes: Optional[str] = Field(None, description="Notas del pago que falló")

    class Config:
        from_attributes = True


class BulkPaymentResponse(BaseModel):
    """Respuesta para pagos múltiples"""
    payments: List[PaymentResponse] = Field(..., description="Lista de pagos creados exitosamente")
    total_payments: int = Field(..., description="Total de pagos enviados en la solicitud")
    total_amount: float = Field(..., description="Monto total de todos los pagos creados exitosamente")
    success_count: int = Field(..., description="Número de pagos creados exitosamente")
    failed_count: int = Field(default=0, description="Número de pagos que fallaron")
    errors: List[PaymentError] = Field(default_factory=list, description="Lista detallada de pagos que fallaron con su razón")

    class Config:
        from_attributes = True
