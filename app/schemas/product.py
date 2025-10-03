from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .product_route_price import ProductRoutePriceSimpleResponse


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0
    sku: str
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    sku: Optional[str] = None
    is_active: Optional[bool] = None


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    route_prices: Optional[List[ProductRoutePriceSimpleResponse]] = None  # Lista de precios por ruta

    class Config:
        from_attributes = True
