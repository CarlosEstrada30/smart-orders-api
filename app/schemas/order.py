from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from ..models.order import OrderStatus
from .client import ClientResponse
from .route import RouteResponse
from .base import TimezoneAwareBaseModel, create_timezone_aware_datetime_field


class OrderItemBase(BaseModel):
    product_id: int
    quantity: float = Field(..., gt=0, description="Quantity must be greater than 0")
    unit_price: float

    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return round(v, 2)  # Redondear a 2 decimales


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemResponse(OrderItemBase):
    id: int
    order_id: int
    total_price: float
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    product_description: Optional[str] = None

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    client_id: int
    route_id: Optional[int] = None
    status: OrderStatus = OrderStatus.PENDING
    discount_amount: Optional[float] = 0.0  # Descuento como cantidad fija de dinero
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    items: List[OrderItemCreate]


class OrderUpdate(BaseModel):
    """Schema for order editing (complete for PENDING orders, basic for others)"""
    client_id: Optional[int] = None
    route_id: Optional[int] = None
    status: Optional[OrderStatus] = None
    discount_amount: Optional[float] = None
    notes: Optional[str] = None
    items: Optional[List[OrderItemCreate]] = None


class OrderResponse(OrderBase, TimezoneAwareBaseModel):
    id: int
    order_number: str
    total_amount: float
    created_at: datetime = create_timezone_aware_datetime_field(
        description="Fecha y hora de creación (en zona horaria del cliente)"
    )
    updated_at: Optional[datetime] = create_timezone_aware_datetime_field(
        default=None,
        description="Fecha y hora de última actualización (en zona horaria del cliente)"
    )
    items: List[OrderItemResponse] = []
    client: Optional[ClientResponse] = None
    route: Optional[RouteResponse] = None


# Analytics Schemas
class MonthlySummary(BaseModel):
    """Schema for monthly orders summary"""
    year: int
    month: int
    month_name: str
    order_count: int
    total_amount: float

    class Config:
        from_attributes = True


class OrderAnalyticsSummary(BaseModel):
    """Schema for orders analytics summary response"""
    monthly_data: List[MonthlySummary]
    total_orders: int
    total_amount: float
    period_start: Optional[str] = None
    period_end: Optional[str] = None

    class Config:
        from_attributes = True


class StatusDistribution(BaseModel):
    """Schema for status distribution (donut chart data)"""
    status: str
    status_name: str
    count: int
    percentage: float

    class Config:
        from_attributes = True


class StatusDistributionSummary(BaseModel):
    """Schema for status distribution summary response (donut chart)"""
    status_data: List[StatusDistribution]
    total_orders: int
    month: int
    year: int
    period_name: str

    class Config:
        from_attributes = True


class BatchOrderUpdateRequest(BaseModel):
    """Schema for batch order status updates"""
    order_ids: List[int] = Field(..., min_items=1, description="List of order IDs to update")
    status: OrderStatus = Field(..., description="New status to set for all orders")
    notes: Optional[str] = Field(None, description="Optional notes for the status change")


class ProductError(BaseModel):
    """Schema for product error details"""
    product_id: int
    product_name: str
    product_sku: str
    error_type: str
    error_message: str
    required_quantity: Optional[float] = None
    available_quantity: Optional[float] = None


class OrderUpdateError(BaseModel):
    """Schema for order update error details"""
    order_id: int
    order_number: Optional[str] = None
    error_type: str
    error_message: str
    products_with_errors: List[ProductError] = Field(default_factory=list, description="Products that caused errors")


class OrderUpdateSuccess(BaseModel):
    """Schema for successful order update details"""
    order_id: int
    order_number: str
    products_updated: List[dict] = Field(default_factory=list, description="Products that were processed")


class BatchOrderUpdateResponse(BaseModel):
    """Schema for batch order update response"""
    updated_count: int
    failed_count: int
    total_orders: int
    status: OrderStatus
    failed_orders: List[int] = Field(default_factory=list, description="Order IDs that failed to update")
    success_orders: List[int] = Field(default_factory=list, description="Order IDs that were updated successfully")
    success_details: List[OrderUpdateSuccess] = Field(default_factory=list, description="Detailed success information")
    failed_details: List[OrderUpdateError] = Field(
        default_factory=list,
        description="Detailed error information for failed orders"
    )
