from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from ..models.order import OrderStatus
from .client import ClientResponse
from .route import RouteResponse


class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


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
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    items: List[OrderItemCreate]


class OrderUpdate(BaseModel):
    route_id: Optional[int] = None
    status: Optional[OrderStatus] = None
    notes: Optional[str] = None


class OrderResponse(OrderBase):
    id: int
    order_number: str
    total_amount: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[OrderItemResponse] = []
    client: Optional[ClientResponse] = None
    route: Optional[RouteResponse] = None

    class Config:
        from_attributes = True


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
