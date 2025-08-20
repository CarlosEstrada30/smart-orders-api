from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from ..models.order import OrderStatus


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

    class Config:
        from_attributes = True


class OrderBase(BaseModel):
    client_id: int
    status: OrderStatus = OrderStatus.PENDING
    notes: Optional[str] = None


class OrderCreate(OrderBase):
    items: List[OrderItemCreate]


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    notes: Optional[str] = None


class OrderResponse(OrderBase):
    id: int
    order_number: str
    total_amount: float
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[OrderItemResponse] = []
    client_name: Optional[str] = None

    class Config:
        from_attributes = True 