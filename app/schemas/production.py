from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class RouteInfo(BaseModel):
    route_id: int
    route_name: str
    date: date


class ProductionSummary(BaseModel):
    total_products: int
    products_needing_production: int


class ProductProductionInfo(BaseModel):
    id: int
    name: str
    sku: str
    stock: int
    total_comprometidos: int
    total_a_producir: int


class ProductionDashboardResponse(BaseModel):
    route_info: RouteInfo
    production_summary: ProductionSummary
    products: List[ProductProductionInfo]


class ProductionDashboardFilters(BaseModel):
    route_id: int
    date: date
    product_category: Optional[str] = None
    priority_level: Optional[str] = None
    min_shortage_value: Optional[float] = None
