from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.product_route_price import ProductRoutePrice
from ..schemas.product_route_price import ProductRoutePriceCreate, ProductRoutePriceUpdate
from .base import BaseRepository


class ProductRoutePriceRepository(BaseRepository[ProductRoutePrice, ProductRoutePriceCreate, ProductRoutePriceUpdate]):
    def __init__(self):
        super().__init__(ProductRoutePrice)

    def get_by_product_and_route(self, db: Session, product_id: int, route_id: int) -> Optional[ProductRoutePrice]:
        """Obtener precio específico de un producto para una ruta"""
        return db.query(ProductRoutePrice).filter(
            ProductRoutePrice.product_id == product_id,
            ProductRoutePrice.route_id == route_id
        ).first()

    def get_by_product(self, db: Session, product_id: int) -> List[ProductRoutePrice]:
        """Obtener todos los precios de un producto por ruta"""
        return db.query(ProductRoutePrice).filter(
            ProductRoutePrice.product_id == product_id
        ).all()

    def get_by_route(self, db: Session, route_id: int) -> List[ProductRoutePrice]:
        """Obtener todos los precios de una ruta"""
        return db.query(ProductRoutePrice).filter(
            ProductRoutePrice.route_id == route_id
        ).all()

    def get_price_for_product_route(self, db: Session, product_id: int, route_id: Optional[int] = None) -> Optional[float]:
        """Obtener el precio de un producto para una ruta específica, o el precio por defecto si no hay ruta"""
        if route_id:
            price_entry = self.get_by_product_and_route(db, product_id, route_id)
            if price_entry:
                return price_entry.price
        
        # Si no hay ruta específica o no se encontró precio para esa ruta,
        # devolver None para que se use el precio por defecto del producto
        return None
