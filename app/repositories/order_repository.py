from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from .base import BaseRepository
from ..models.order import Order, OrderItem, OrderStatus
from ..schemas.order import OrderCreate, OrderUpdate, OrderItemCreate
import uuid


class OrderRepository(BaseRepository[Order, OrderCreate, OrderUpdate]):
    def __init__(self):
        super().__init__(Order)

    def get_by_order_number(self, db: Session, *, order_number: str) -> Optional[Order]:
        return db.query(Order).options(
            joinedload(Order.client),
            joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(Order.order_number == order_number).first()

    def get_orders_by_client(self, db: Session, *, client_id: int, skip: int = 0, limit: int = 100) -> List[Order]:
        return db.query(Order).options(
            joinedload(Order.client),
            joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(Order.client_id == client_id).offset(skip).limit(limit).all()

    def get_orders_by_status(self, db: Session, *, status: OrderStatus, skip: int = 0, limit: int = 100) -> List[Order]:
        return db.query(Order).options(
            joinedload(Order.client),
            joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(Order.status == status).offset(skip).limit(limit).all()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Order]:
        return db.query(Order).options(
            joinedload(Order.client),
            joinedload(Order.items).joinedload(OrderItem.product)
        ).offset(skip).limit(limit).all()

    def get(self, db: Session, id: int) -> Optional[Order]:
        return db.query(Order).options(
            joinedload(Order.client),
            joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(Order.id == id).first()

    def create_order_with_items(self, db: Session, *, order_data: OrderCreate) -> Order:
        # Generate unique order number
        order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate total amount
        total_amount = sum(item.quantity * item.unit_price for item in order_data.items)
        
        # Create order
        order = Order(
            order_number=order_number,
            client_id=order_data.client_id,
            status=order_data.status,
            total_amount=total_amount,
            notes=order_data.notes
        )
        db.add(order)
        db.flush()  # Get the order ID
        
        # Create order items
        for item_data in order_data.items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                total_price=item_data.quantity * item_data.unit_price
            )
            db.add(order_item)
        
        db.commit()
        db.refresh(order)
        
        # Load relationships for the response
        db.refresh(order)
        return order

    def update_order_status(self, db: Session, *, order_id: int, status: OrderStatus) -> Optional[Order]:
        order = self.get(db, order_id)
        if order:
            order.status = status
            db.commit()
            db.refresh(order)
        return order 