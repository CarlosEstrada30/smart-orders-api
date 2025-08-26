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