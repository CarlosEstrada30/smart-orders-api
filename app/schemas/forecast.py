from typing import List, Optional
from pydantic import BaseModel


class ForecastPoint(BaseModel):
    """Predicted quantity for a single product on a single day."""
    date: str                   # "2026-03-26"
    predicted: float            # raw estimated units (statistical)
    recommended: int            # ceil(predicted * 1.10) — what to produce
    last_week_actual: Optional[float] = None  # actual units sold same weekday last week
    is_no_delivery_day: bool = False          # True when this weekday historically has no orders


class RouteBreakdown(BaseModel):
    """Estimated contribution of a route to a product's demand."""
    route_id: Optional[int] = None
    route_name: str
    predicted: float
    recommended: int


class ProductForecast(BaseModel):
    """Forecast for a single product over the next N days."""
    product_id: int
    product_name: str
    forecast: List[ForecastPoint]
    by_route: List[RouteBreakdown]
    trend_direction: str        # "up" | "down" | "stable"
    trend_percentage: float     # e.g. +12.5 or -5.3
    confidence: str             # "alta" | "media" | "baja"
    history_days_available: int


class ForecastResponse(BaseModel):
    """Full production forecast response."""
    products: List[ProductForecast]
    days_ahead: int
    history_days_used: int
    generated_at: str
    total_recommended_tomorrow: int   # sum of all recommended units for day 1
