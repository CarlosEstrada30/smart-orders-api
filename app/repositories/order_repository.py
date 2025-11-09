from typing import Optional, List, Union
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from datetime import datetime, date
from decimal import Decimal
from .base import BaseRepository
from ..models.order import Order, OrderItem, OrderStatus
from ..schemas.order import OrderCreate, OrderUpdate
import uuid


class OrderRepository(BaseRepository[Order, OrderCreate, OrderUpdate]):
    def __init__(self):
        super().__init__(Order)

    def get_by_order_number(
            self,
            db: Session,
            *,
            order_number: str) -> Optional[Order]:
        return db.query(Order).options(
            joinedload(Order.client),
            joinedload(Order.route),
            joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(Order.order_number == order_number).first()

    def get_orders_by_client(
            self,
            db: Session,
            *,
            client_id: int,
            skip: int = 0,
            limit: int = 100) -> List[Order]:
        return db.query(Order).options(
            joinedload(Order.client),
            joinedload(Order.route),
            joinedload(Order.items).joinedload(OrderItem.product)
        ).filter(Order.client_id == client_id).offset(skip).limit(limit).all()

    def get_orders_by_status(
            self,
            db: Session,
            *,
            status: OrderStatus,
            skip: int = 0,
            limit: int = 100) -> List[Order]:
        from sqlalchemy import text

        # Use raw SQL for status filtering to avoid enum mapping issues
        # Convert to uppercase to match database values (DB has UPPERCASE,
        # Python enum has lowercase)
        status_value = status.value if hasattr(
            status, 'value') else str(status)
        status_value_upper = status_value.upper()

        return db.query(Order).options(
            joinedload(
                Order.client),
            joinedload(
                Order.route),
            joinedload(
                Order.items).joinedload(
                    OrderItem.product)).filter(
                        text("orders.status = :status")).params(
                            status=status_value_upper).offset(skip).limit(limit).all()

    def get_multi(self, db: Session, *, skip: int = 0,
                  limit: int = 100) -> List[Order]:
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

    def create_order_with_items(
            self,
            db: Session,
            *,
            order_data: OrderCreate) -> Order:
        # Generate unique order number
        order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"

        # Calculate total amount
        subtotal = sum(
            item.quantity *
            item.unit_price for item in order_data.items)

        # Apply discount if provided
        discount_amount = getattr(order_data, 'discount_amount', 0.0) or 0.0
        if discount_amount > 0:
            total_amount = subtotal - discount_amount
        else:
            total_amount = subtotal

        # Create order
        order = Order(
            order_number=order_number,
            client_id=order_data.client_id,
            route_id=order_data.route_id,
            status=order_data.status,
            total_amount=total_amount,
            discount_amount=discount_amount,
            notes=order_data.notes,
            balance_due=total_amount  # Inicializar balance_due igual a total_amount
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

    def update_order_status(
            self,
            db: Session,
            *,
            order_id: int,
            status: OrderStatus) -> Optional[Order]:
        order = self.get(db, order_id)
        if order:
            order.status = status
            db.commit()
            db.refresh(order)
        return order

    def update_pending_order_complete(
            self,
            db: Session,
            *,
            order_id: int,
            order_update) -> Optional[Order]:
        """
        Update a PENDING order completely (client, items, route, notes)
        LACTEOS FLOW: Complete update for PENDING orders
        """
        # Get the existing order
        order = self.get(db, order_id)
        if not order:
            return None

        # Update basic fields if provided
        if order_update.client_id is not None:
            order.client_id = order_update.client_id
        if order_update.route_id is not None:
            order.route_id = order_update.route_id
        if order_update.notes is not None:
            order.notes = order_update.notes
        
        # Handle discount_amount update
        # If items are being updated, discount_amount should default to 0 if not provided
        # If items are not being updated but discount_amount is provided, update it
        if order_update.items is not None:
            # Items are being updated - reset discount_amount to 0 if not explicitly provided
            if order_update.discount_amount is not None:
                order.discount_amount = order_update.discount_amount
            else:
                order.discount_amount = 0.0
        elif order_update.discount_amount is not None:
            # Items are not being updated, but discount_amount is provided
            order.discount_amount = order_update.discount_amount
            # Recalculate total amount with new discount using existing items
            # Convert both quantity (Decimal) and unit_price (float) to Decimal for calculation
            subtotal = sum(
                Decimal(str(item.quantity)) * Decimal(str(item.unit_price))
                for item in order.items
            )
            discount_decimal = Decimal(str(order_update.discount_amount))
            if order_update.discount_amount > 0:
                order.total_amount = float(subtotal - discount_decimal)
            else:
                order.total_amount = float(subtotal)

        # If items are provided, replace all items
        if order_update.items is not None:
            # Delete existing items
            db.query(OrderItem).filter(OrderItem.order_id == order_id).delete()

            # Create new items
            total_amount = 0
            for item_data in order_update.items:
                item_total = item_data.quantity * item_data.unit_price
                total_amount += item_total

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item_data.product_id,
                    quantity=item_data.quantity,
                    unit_price=item_data.unit_price,
                    total_price=item_total
                )
                db.add(order_item)

            # Apply discount to total amount
            # Use the discount_amount we already set above (either from update or 0.0)
            if order.discount_amount and order.discount_amount > 0:
                order.total_amount = total_amount - order.discount_amount
            else:
                order.total_amount = total_amount

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
        date_from: Optional[Union[date, datetime]] = None,
        date_to: Optional[Union[date, datetime]] = None,
        search: Optional[str] = None,
        client_timezone: Optional[str] = None
    ) -> List[Order]:
        """Get orders with optional filters for status, route, date range, and search
        
        Args:
            client_timezone: If provided, converts created_at to this timezone for date comparisons.
                            This allows filtering by date in the client's timezone regardless of
                            the database timezone.
        """
        from ..models.client import Client
        from sqlalchemy import text, func

        query = db.query(Order).options(
            joinedload(Order.client),
            joinedload(Order.route),
            joinedload(Order.items).joinedload(OrderItem.product)
        )

        # Build filters dynamically
        filters = []

        if status is not None:
            # Convert to uppercase to match database values
            status_value = status.value if hasattr(
                status, 'value') else str(status)
            status_value_upper = status_value.upper()
            filters.append(
                text("orders.status = :status").params(
                    status=status_value_upper))

        if route_id is not None:
            filters.append(Order.route_id == route_id)

        if date_from is not None:
            if client_timezone and isinstance(date_from, date):
                # Convert created_at to client timezone and compare with date
                # PostgreSQL: created_at is timestamp with timezone, convert to client timezone
                filters.append(
                    text(
                        "DATE(orders.created_at AT TIME ZONE :tz) >= :date_from"
                    ).params(tz=client_timezone, date_from=date_from)
                )
            elif isinstance(date_from, date):
                # Include orders from the beginning of date_from (no timezone conversion)
                filters.append(
                    Order.created_at >= datetime.combine(
                        date_from, datetime.min.time()))
            else:
                # date_from is already a datetime
                filters.append(Order.created_at >= date_from)

        if date_to is not None:
            if client_timezone and isinstance(date_to, date):
                # Convert created_at to client timezone and compare with date
                filters.append(
                    text(
                        "DATE(orders.created_at AT TIME ZONE :tz) <= :date_to"
                    ).params(tz=client_timezone, date_to=date_to)
                )
            elif isinstance(date_to, date):
                # Include orders until the end of date_to (no timezone conversion)
                filters.append(
                    Order.created_at <= datetime.combine(
                        date_to, datetime.max.time()))
            else:
                # date_to is already a datetime
                filters.append(Order.created_at <= date_to)

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

        return query.order_by(Order.created_at.desc()).offset(
            skip).limit(limit).all()

    def count_orders_with_filters(
        self,
        db: Session,
        *,
        status: Optional[OrderStatus] = None,
        route_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        search: Optional[str] = None,
        client_timezone: Optional[str] = None
    ) -> int:
        """Count orders with optional filters for status, route, date range, and search"""
        from ..models.client import Client
        from sqlalchemy import text

        query = db.query(Order)

        # Build filters dynamically (same logic as get_orders_with_filters)
        filters = []

        if status is not None:
            # Convert to uppercase to match database values
            status_value = status.value if hasattr(
                status, 'value') else str(status)
            status_value_upper = status_value.upper()
            filters.append(
                text("orders.status = :status").params(
                    status=status_value_upper))

        if route_id is not None:
            filters.append(Order.route_id == route_id)

        if date_from is not None:
            if client_timezone and isinstance(date_from, date):
                # Convert created_at to client timezone and compare with date
                filters.append(
                    text(
                        "DATE(orders.created_at AT TIME ZONE :tz) >= :date_from"
                    ).params(tz=client_timezone, date_from=date_from)
                )
            elif isinstance(date_from, date):
                # Include orders from the beginning of date_from (no timezone conversion)
                filters.append(
                    Order.created_at >= datetime.combine(
                        date_from, datetime.min.time()))
            else:
                # date_from is already a datetime
                filters.append(Order.created_at >= date_from)

        if date_to is not None:
            if client_timezone and isinstance(date_to, date):
                # Convert created_at to client timezone and compare with date
                filters.append(
                    text(
                        "DATE(orders.created_at AT TIME ZONE :tz) <= :date_to"
                    ).params(tz=client_timezone, date_to=date_to)
                )
            elif isinstance(date_to, date):
                # Include orders until the end of date_to (no timezone conversion)
                filters.append(
                    Order.created_at <= datetime.combine(
                        date_to, datetime.max.time()))
            else:
                # date_to is already a datetime
                filters.append(Order.created_at <= date_to)

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

    def get_monthly_summary_by_status(
        self,
        db: Session,
        *,
        status: OrderStatus,
        year: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[dict]:
        """Get monthly summary of orders by status with optional year/date range filters"""
        from sqlalchemy import func, extract

        # Base query with aggregation
        query = db.query(
            extract('year', Order.created_at).label('year'),
            extract('month', Order.created_at).label('month'),
            func.count(Order.id).label('order_count'),
            func.sum(Order.total_amount).label('total_amount')
        )

        # Build filters
        filters = []

        # Status filter (direct enum comparison)
        filters.append(Order.status == status)

        # Year filter
        if year is not None:
            filters.append(extract('year', Order.created_at) == year)

        # Date range filters
        if start_date is not None:
            filters.append(
                Order.created_at >= datetime.combine(start_date, datetime.min.time())
            )

        if end_date is not None:
            filters.append(
                Order.created_at <= datetime.combine(end_date, datetime.max.time())
            )

        # Apply filters
        query = query.filter(and_(*filters))

        # Group by year and month, order by year and month
        query = query.group_by(
            extract('year', Order.created_at),
            extract('month', Order.created_at)
        ).order_by(
            extract('year', Order.created_at),
            extract('month', Order.created_at)
        )

        return [
            {
                'year': int(row.year),
                'month': int(row.month),
                'order_count': int(row.order_count),
                'total_amount': float(row.total_amount or 0)
            }
            for row in query.all()
        ]

    def get_status_distribution_by_month(
        self,
        db: Session,
        *,
        year: int,
        month: int
    ) -> List[dict]:
        """Get count of orders by status for a specific month/year"""
        from sqlalchemy import func, extract

        # Base query with aggregation by status
        query = db.query(
            Order.status.label('status'),
            func.count(Order.id).label('count')
        )

        # Filter by specific month and year
        query = query.filter(
            extract('year', Order.created_at) == year,
            extract('month', Order.created_at) == month
        )

        # Group by status
        query = query.group_by(Order.status)

        return [
            {
                'status': str(row.status),
                'count': int(row.count)
            }
            for row in query.all()
        ]
