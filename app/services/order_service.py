from typing import Optional, List
from sqlalchemy.orm import Session
from ..repositories.order_repository import OrderRepository
from ..repositories.client_repository import ClientRepository
from ..repositories.product_repository import ProductRepository
from ..schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderItemCreate
from ..models.order import Order, OrderStatus
from .product_service import ProductService


class OrderService:
    def __init__(self):
        self.order_repository = OrderRepository()
        self.client_repository = ClientRepository()
        self.product_repository = ProductRepository()
        self.product_service = ProductService()

    def get_order(self, db: Session, order_id: int) -> Optional[Order]:
        return self.order_repository.get(db, order_id)

    def get_order_by_number(self, db: Session, order_number: str) -> Optional[Order]:
        return self.order_repository.get_by_order_number(db, order_number=order_number)

    def get_orders(self, db: Session, skip: int = 0, limit: int = 100) -> List[Order]:
        return self.order_repository.get_multi(db, skip=skip, limit=limit)

    def get_orders_by_client(self, db: Session, client_id: int) -> List[Order]:
        return self.order_repository.get_orders_by_client(db, client_id=client_id)

    def get_orders_by_status(self, db: Session, status: OrderStatus) -> List[Order]:
        return self.order_repository.get_orders_by_status(db, status=status)

    def create_order(self, db: Session, order_data: OrderCreate) -> Order:
        # Validate client exists and is active
        client = self.client_repository.get(db, order_data.client_id)
        if not client or not client.is_active:
            raise ValueError("Client not found or inactive")

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
            return self.order_repository.create_order_with_items(db, order_data=order_data)
        except Exception as e:
            # If order creation fails, restore stock
            for item in order_data.items:
                self.product_service.update_stock(db, item.product_id, item.quantity)
            raise e

    def update_order_status(self, db: Session, order_id: int, status: OrderStatus) -> Optional[Order]:
        order = self.order_repository.get(db, order_id)
        if not order:
            return None

        # Validate status transition
        if not self._is_valid_status_transition(order.status, status):
            raise ValueError(f"Invalid status transition from {order.status} to {status}")

        return self.order_repository.update_order_status(db, order_id=order_id, status=status)

    def cancel_order(self, db: Session, order_id: int) -> Optional[Order]:
        order = self.order_repository.get(db, order_id)
        if not order:
            return None

        # Only allow cancellation of pending or confirmed orders
        if order.status not in [OrderStatus.PENDING, OrderStatus.CONFIRMED]:
            raise ValueError(f"Cannot cancel order with status {order.status}")

        # Restore stock for all items
        for item in order.items:
            self.product_service.update_stock(db, item.product_id, item.quantity)

        return self.order_repository.update_order_status(db, order_id=order_id, status=OrderStatus.CANCELLED)

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