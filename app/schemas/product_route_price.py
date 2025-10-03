from pydantic import BaseModel
from typing import Optional


class ProductRoutePriceBase(BaseModel):
    product_id: int
    route_id: int
    price: float


class ProductRoutePriceCreate(ProductRoutePriceBase):
    pass


class ProductRoutePriceUpdate(BaseModel):
    price: Optional[float] = None


class ProductRoutePriceResponse(ProductRoutePriceBase):
    id: int
    product_name: Optional[str] = None
    route_name: Optional[str] = None

    class Config:
        from_attributes = True


class ProductRoutePriceSimpleResponse(BaseModel):
    """Simplified response with only essential fields"""
    product_id: int
    route_id: int
    price: float
    route_name: Optional[str] = None

    class Config:
        from_attributes = True
