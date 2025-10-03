from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from typing import List, Dict
from datetime import date
from collections import defaultdict

from ..models.order import Order, OrderStatus
from ..models.product import Product
from ..models.route import Route
from ..schemas.production import (
    ProductionDashboardResponse,
    RouteInfo,
    ProductionSummary,
    ProductProductionInfo
)


class ProductionService:
    """Servicio para el dashboard de producción"""

    def get_production_dashboard(
        self,
        route_id: int,
        target_date: date,
        db: Session
    ) -> ProductionDashboardResponse:
        """
        Genera el dashboard de producción para una ruta y fecha específica
        """
        # Obtener información de la ruta
        route = db.query(Route).filter(Route.id == route_id).first()
        if not route:
            raise ValueError(f"Ruta con ID {route_id} no encontrada")

        # Obtener órdenes pendientes de la ruta para la fecha
        pending_orders = self._get_pending_orders_for_route(db, route_id, target_date)

        # Obtener stock actual de productos
        current_stock = self._get_current_stock(db)

        # Calcular información de producción por producto
        products_info = self._calculate_production_info(db, pending_orders, current_stock)

        # Generar resumen
        summary = self._generate_production_summary(products_info)

        # Crear respuesta
        route_info = RouteInfo(
            route_id=route.id,
            route_name=route.name,
            date=target_date
        )

        return ProductionDashboardResponse(
            route_info=route_info,
            production_summary=summary,
            products=products_info
        )

    def _get_pending_orders_for_route(self, db: Session, route_id: int, target_date: date) -> List[Order]:
        """Obtiene órdenes pendientes de una ruta para una fecha específica"""
        return db.query(Order).filter(
            and_(
                Order.route_id == route_id,
                func.date(Order.created_at) == target_date,
                Order.status == OrderStatus.PENDING.value
            )
        ).all()

    def _get_current_stock(self, db: Session) -> Dict[int, int]:
        """Obtiene el stock actual de todos los productos"""
        products = db.query(Product.id, Product.stock).all()
        return {product.id: product.stock for product in products}

    def _calculate_production_info(
        self,
        db: Session,
        pending_orders: List[Order],
        current_stock: Dict[int, int]
    ) -> List[ProductProductionInfo]:
        """Calcula la información de producción para cada producto"""
        products_info = []

        # Consolidar productos comprometidos por producto
        product_committed = defaultdict(int)

        for order in pending_orders:
            for item in order.items:
                product_id = item.product_id
                quantity = item.quantity
                product_committed[product_id] += quantity

        # Obtener todos los productos que tienen stock o están comprometidos
        all_product_ids = set(current_stock.keys()) | set(product_committed.keys())

        if not all_product_ids:
            return []

        products = db.query(Product).filter(Product.id.in_(all_product_ids)).all()

        for product in products:
            product_id = product.id
            stock_actual = current_stock.get(product_id, 0)
            total_comprometidos = product_committed.get(product_id, 0)

            # Total a producir: si los comprometidos superan el stock
            total_a_producir = max(0, total_comprometidos - stock_actual)

            products_info.append(ProductProductionInfo(
                id=product.id,
                name=product.name,
                sku=product.sku or "",
                stock=stock_actual,
                total_comprometidos=total_comprometidos,
                total_a_producir=total_a_producir
            ))

        # Ordenar por total a producir (mayor primero)
        products_info.sort(key=lambda x: x.total_a_producir, reverse=True)

        return products_info

    def _generate_production_summary(self, products_info: List[ProductProductionInfo]) -> ProductionSummary:
        """Genera el resumen de producción"""
        total_products = len(products_info)
        products_needing_production = len([p for p in products_info if p.total_a_producir > 0])

        return ProductionSummary(
            total_products=total_products,
            products_needing_production=products_needing_production
        )
