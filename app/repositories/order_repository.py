from typing import Optional, List
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from datetime import datetime, date
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
            joinedload(Order.route),
            joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(Order.order_number == order_number).first()

    def get_orders_by_client(self, db: Session, *, client_id: int, skip: int = 0, limit: int = 100) -> List[Order]:
        return db.query(Order).options(
            joinedload(Order.client),
            joinedload(Order.route),
            joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(Order.client_id == client_id).offset(skip).limit(limit).all()

    def get_orders_by_status(self, db: Session, *, status: OrderStatus, skip: int = 0, limit: int = 100) -> List[Order]:
        from sqlalchemy import text
        
        # Use raw SQL for status filtering to avoid enum mapping issues
        # Convert to uppercase to match database values (DB has UPPERCASE, Python enum has lowercase)
        status_value = status.value if hasattr(status, 'value') else str(status)
        status_value_upper = status_value.upper()
        
        return db.query(Order).options(
            joinedload(Order.client),
            joinedload(Order.route),
            joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(text("orders.status = :status")).params(status=status_value_upper).offset(skip).limit(limit).all()

    def get_multi(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[Order]:
        return db.query(Order).options(
            joinedload(Order.client),
            joinedload(Order.route),
            joinedload(Order.items).joinedload(OrderItem.product)
        ).order_by(Order.created_at.desc()).offset(skip).limit(limit).all()

    def get(self, db: Session, id: int) -> Optional[Order]:
        return db.query(Order).options(
            joinedload(Order.client),
            joinedload(Order.route),
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
            route_id=order_data.route_id,
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

    def get_orders_with_filters(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[OrderStatus] = None,
        route_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        search: Optional[str] = None
    ) -> List[Order]:
        """Get orders with optional filters for status, route, date range, and search"""
        from ..models.client import Client
        
        query = db.query(Order).options(
            joinedload(Order.client),
            joinedload(Order.route),
            joinedload(Order.items).joinedload(OrderItem.product)
        )
        
        # Build filters dynamically
        filters = []
        
        if status is not None:
            from sqlalchemy import text
            # Convert to uppercase to match database values
            status_value = status.value if hasattr(status, 'value') else str(status)
            status_value_upper = status_value.upper()
            filters.append(text("orders.status = :status").params(status=status_value_upper))
        
        if route_id is not None:
            filters.append(Order.route_id == route_id)
        
        if date_from is not None:
            # Include orders from the beginning of date_from
            filters.append(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
        
        if date_to is not None:
            # Include orders until the end of date_to
            filters.append(Order.created_at <= datetime.combine(date_to, datetime.max.time()))
        
        if search is not None and search.strip():
            # Search in order number or client name (case-insensitive)
            search_term = f"%{search.strip()}%"
            search_filters = or_(
                Order.order_number.ilike(search_term),
                Client.name.ilike(search_term)
            )
            filters.append(search_filters)
            # Join with Client table for name search
            query = query.join(Client, Order.client_id == Client.id)
        
        # Apply filters if any
        if filters:
            query = query.filter(and_(*filters))
        
        return query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()

    def count_orders_with_filters(
        self, 
        db: Session, 
        *, 
        status: Optional[OrderStatus] = None,
        route_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        search: Optional[str] = None
    ) -> int:
        """Count orders with optional filters for status, route, date range, and search"""
        from ..models.client import Client
        
        query = db.query(Order)
        
        # Build filters dynamically (same logic as get_orders_with_filters)
        filters = []
        
        if status is not None:
            from sqlalchemy import text
            # Convert to uppercase to match database values
            status_value = status.value if hasattr(status, 'value') else str(status)
            status_value_upper = status_value.upper()
            filters.append(text("orders.status = :status").params(status=status_value_upper))
        
        if route_id is not None:
            filters.append(Order.route_id == route_id)
        
        if date_from is not None:
            # Include orders from the beginning of date_from
            filters.append(Order.created_at >= datetime.combine(date_from, datetime.min.time()))
        
        if date_to is not None:
            # Include orders until the end of date_to
            filters.append(Order.created_at <= datetime.combine(date_to, datetime.max.time()))
        
        if search is not None and search.strip():
            # Search in order number or client name (case-insensitive)
            search_term = f"%{search.strip()}%"
            search_filters = or_(
                Order.order_number.ilike(search_term),
                Client.name.ilike(search_term)
            )
            filters.append(search_filters)
            # Join with Client table for name search
            query = query.join(Client, Order.client_id == Client.id)
        
        # Apply filters if any
        if filters:
            query = query.filter(and_(*filters))
        
        return query.count() 