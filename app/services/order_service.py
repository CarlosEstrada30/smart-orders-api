from typing import Optional, List
from datetime import date
from sqlalchemy.orm import Session
from ..repositories.order_repository import OrderRepository
from ..repositories.client_repository import ClientRepository
from ..repositories.product_repository import ProductRepository
from ..repositories.route_repository import RouteRepository
from ..schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderItemCreate, OrderItemResponse
from ..schemas.pagination import PaginatedResponse
from ..models.order import Order, OrderStatus
from .product_service import ProductService


class OrderService:
    def __init__(self):
        self.order_repository = OrderRepository()
        self.client_repository = ClientRepository()
        self.product_repository = ProductRepository()
        self.route_repository = RouteRepository()
        self.product_service = ProductService()

    def _process_order_items(self, order: Order) -> List[OrderItemResponse]:
        """Process order items and populate product information"""
        processed_items = []
        for item in order.items:
            item_data = {
                "id": item.id,
                "order_id": item.order_id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "total_price": item.total_price,
                "product_name": item.product.name if item.product else None,
                "product_sku": item.product.sku if item.product else None,
                "product_description": item.product.description if item.product else None
            }
            processed_items.append(OrderItemResponse(**item_data))
        return processed_items

    def _process_order_response(self, order: Order) -> OrderResponse:
        """Process order and create response with complete data"""
        # Process items
        processed_items = self._process_order_items(order)
        
        # Create order response
        order_data = {
            "id": order.id,
            "order_number": order.order_number,
            "client_id": order.client_id,
            "route_id": order.route_id,
            "status": order.status,
            "total_amount": order.total_amount,
            "notes": order.notes,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "items": processed_items,
            "client": order.client,
            "route": order.route
        }
        return OrderResponse(**order_data)

    def get_order(self, db: Session, order_id: int) -> Optional[OrderResponse]:
        order = self.order_repository.get(db, order_id)
        if not order:
            return None
        return self._process_order_response(order)

    def get_order_by_number(self, db: Session, order_number: str) -> Optional[OrderResponse]:
        order = self.order_repository.get_by_order_number(db, order_number=order_number)
        if not order:
            return None
        return self._process_order_response(order)

    def get_orders(self, db: Session, skip: int = 0, limit: int = 100) -> List[OrderResponse]:
        orders = self.order_repository.get_multi(db, skip=skip, limit=limit)
        return [self._process_order_response(order) for order in orders]

    def get_orders_by_client(self, db: Session, client_id: int, skip: int = 0, limit: int = 100) -> List[OrderResponse]:
        orders = self.order_repository.get_orders_by_client(db, client_id=client_id, skip=skip, limit=limit)
        return [self._process_order_response(order) for order in orders]

    def get_orders_by_status(self, db: Session, status: OrderStatus, skip: int = 0, limit: int = 100) -> List[OrderResponse]:
        orders = self.order_repository.get_orders_by_status(db, status=status, skip=skip, limit=limit)
        return [self._process_order_response(order) for order in orders]

    def get_orders_with_filters(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[OrderStatus] = None,
        route_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        search: Optional[str] = None
    ) -> List[OrderResponse]:
        """Get orders with optional filters for status, route, date range, and search"""
        orders = self.order_repository.get_orders_with_filters(
            db, 
            skip=skip, 
            limit=limit, 
            status=status, 
            route_id=route_id, 
            date_from=date_from, 
            date_to=date_to,
            search=search
        )
        return [self._process_order_response(order) for order in orders]

    def get_orders_paginated(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[OrderStatus] = None,
        route_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        search: Optional[str] = None
    ) -> PaginatedResponse[OrderResponse]:
        """Get orders with pagination metadata"""
        # Check if any filters are applied
        has_filters = any([status, route_id, date_from, date_to, search])
        
        if has_filters:
            # Use filtered method
            orders = self.order_repository.get_orders_with_filters(
                db, 
                skip=skip, 
                limit=limit, 
                status=status, 
                route_id=route_id, 
                date_from=date_from, 
                date_to=date_to,
                search=search
            )
            
            # Get total count with same filters
            total = self.order_repository.count_orders_with_filters(
                db, 
                status=status, 
                route_id=route_id, 
                date_from=date_from, 
                date_to=date_to,
                search=search
            )
        else:
            # Use unfiltered method
            orders = self.order_repository.get_multi(db, skip=skip, limit=limit)
            # For total count without filters, we need a simple count
            total = db.query(self.order_repository.model).count()
        
        # Process orders
        processed_orders = [self._process_order_response(order) for order in orders]
        
        # Create paginated response
        return PaginatedResponse.create(
            items=processed_orders,
            total=total,
            skip=skip,
            limit=limit
        )

    def create_order(self, db: Session, order_data: OrderCreate) -> OrderResponse:
        # Validate client exists and is active
        client = self.client_repository.get(db, order_data.client_id)
        if not client or not client.is_active:
            raise ValueError("Client not found or inactive")
        
        # Validate route exists and is active (if provided)
        if order_data.route_id:
            route = self.route_repository.get(db, order_data.route_id)
            if not route or not route.is_active:
                raise ValueError("Route not found or inactive")

        # Validate all products exist, are active, and have sufficient stock
        for item in order_data.items:
            product = self.product_repository.get(db, item.product_id)
            if not product or not product.is_active:
                raise ValueError(f"Product {item.product_id} not found or inactive")
            
            if not self.product_service.check_stock_availability(db, item.product_id, item.quantity):
                raise ValueError(f"Insufficient stock for product {product.name}")

        # Reserve stock for all items
        for item in order_data.items:
            if not self.product_service.reserve_stock(db, item.product_id, item.quantity):
                raise ValueError(f"Failed to reserve stock for product {item.product_id}")

        # Create the order
        try:
            order = self.order_repository.create_order_with_items(db, order_data=order_data)
            return self._process_order_response(order)
        except Exception as e:
            # If order creation fails, restore stock
            for item in order_data.items:
                self.product_service.update_stock(db, item.product_id, item.quantity)
            raise e

    def update_order_status(self, db: Session, order_id: int, status: OrderStatus) -> Optional[OrderResponse]:
        order = self.order_repository.update_order_status(db, order_id=order_id, status=status)
        if not order:
            return None
        return self._process_order_response(order)

    def cancel_order(self, db: Session, order_id: int) -> Optional[OrderResponse]:
        order = self.order_repository.get(db, order_id)
        if not order:
            return None

        # Only allow cancellation of pending or confirmed orders
        if order.status not in [OrderStatus.PENDING, OrderStatus.CONFIRMED]:
            raise ValueError(f"Cannot cancel order with status {order.status}")

        # Restore stock for all items
        for item in order.items:
            self.product_service.update_stock(db, item.product_id, item.quantity)

        updated_order = self.order_repository.update_order_status(db, order_id=order_id, status=OrderStatus.CANCELLED)
        return self._process_order_response(updated_order)

    def _is_valid_status_transition(self, current_status: OrderStatus, new_status: OrderStatus) -> bool:
        """Validate if the status transition is allowed"""
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED],
            OrderStatus.IN_PROGRESS: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
            OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
            OrderStatus.DELIVERED: [],
            OrderStatus.CANCELLED: []
        }
        
        return new_status in valid_transitions.get(current_status, [])

    def get_order_summary(self, db: Session, order_id: int) -> Optional[dict]:
        """Get a summary of the order with client and product details"""
        order = self.order_repository.get(db, order_id)
        if not order:
            return None

        return {
            "order_number": order.order_number,
            "client_name": order.client.name,
            "client_email": order.client.email,
            "status": order.status,
            "total_amount": order.total_amount,
            "created_at": order.created_at,
            "items_count": len(order.items),
            "items": [
                {
                    "product_name": item.product.name,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "total_price": item.total_price
                }
                for item in order.items
            ]
        } 