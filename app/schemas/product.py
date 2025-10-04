from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime
import uuid
from .product_route_price import ProductRoutePriceSimpleResponse


class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 0
    sku: Optional[str] = None
    is_active: bool = True

    @field_validator('sku', mode='before')
    @classmethod
    def generate_sku_if_empty(cls, v):
        if v is None or v == "":
            # Generar SKU automático con formato PROD-XXXXXXXX
            return f"PROD-{uuid.uuid4().hex[:8].upper()}"
        return v


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    sku: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator('sku', mode='before')
    @classmethod
    def validate_sku_update(cls, v):
        # Para actualizaciones, no generamos SKU automático si está vacío
        # Solo permitimos actualizar con un SKU válido o mantener el existente
        if v == "":
            return None
        return v


class ProductResponse(ProductBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    # Lista de precios por ruta
    route_prices: Optional[List[ProductRoutePriceSimpleResponse]] = None

    class Config:
        from_attributes = True
