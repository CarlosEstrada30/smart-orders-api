from typing import Optional, List, Union
from datetime import date, datetime
from sqlalchemy.orm import Session
from ..repositories.order_repository import OrderRepository
from ..repositories.client_repository import ClientRepository
from ..repositories.product_repository import ProductRepository
from ..repositories.route_repository import RouteRepository
from ..schemas.order import OrderCreate, OrderResponse, OrderItemResponse, OrderUpdate
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
                "product_description": item.product.description if item.product else None}
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
            "discount_percentage": order.discount_percentage,
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

    def get_order_by_number(
            self,
            db: Session,
            order_number: str) -> Optional[OrderResponse]:
        order = self.order_repository.get_by_order_number(
            db, order_number=order_number)
        if not order:
            return None
        return self._process_order_response(order)

    def get_orders(self, db: Session, skip: int = 0,
                   limit: int = 100) -> List[OrderResponse]:
        orders = self.order_repository.get_multi(db, skip=skip, limit=limit)
        return [self._process_order_response(order) for order in orders]

    def get_orders_by_client(
            self,
            db: Session,
            client_id: int,
            skip: int = 0,
            limit: int = 100) -> List[OrderResponse]:
        orders = self.order_repository.get_orders_by_client(
            db, client_id=client_id, skip=skip, limit=limit)
        return [self._process_order_response(order) for order in orders]

    def get_orders_by_status(
            self,
            db: Session,
            status: OrderStatus,
            skip: int = 0,
            limit: int = 100) -> List[OrderResponse]:
        orders = self.order_repository.get_orders_by_status(
            db, status=status, skip=skip, limit=limit)
        return [self._process_order_response(order) for order in orders]

    def get_orders_with_filters(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[OrderStatus] = None,
        route_id: Optional[int] = None,
        date_from: Optional[Union[date, datetime]] = None,
        date_to: Optional[Union[date, datetime]] = None,
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
            orders = self.order_repository.get_multi(
                db, skip=skip, limit=limit)
            # For total count without filters, we need a simple count
            total = db.query(self.order_repository.model).count()

        # Process orders
        processed_orders = [
            self._process_order_response(order) for order in orders]

        # Create paginated response
        return PaginatedResponse.create(
            items=processed_orders,
            total=total,
            skip=skip,
            limit=limit
        )

    def _validate_client(self, db: Session, client_id: int):
        """Validate client exists and is active"""
        client = self.client_repository.get(db, client_id)
        if not client or not client.is_active:
            raise ValueError("Client not found or inactive")

    def _validate_route(self, db: Session, route_id: Optional[int]):
        """Validate route exists and is active if provided"""
        if route_id:
            route = self.route_repository.get(db, route_id)
            if not route or not route.is_active:
                raise ValueError("Route not found or inactive")

    def _validate_products_and_stock(self, db: Session, items):
        """Validate all products exist, are active, and have sufficient stock"""
        for item in items:
            product = self.product_repository.get(db, item.product_id)
            if not product or not product.is_active:
                raise ValueError(
                    f"Product {item.product_id} not found or inactive")

            if not self.product_service.check_stock_availability(
                    db, item.product_id, item.quantity):
                raise ValueError(
                    f"Insufficient stock for product {product.name}")

    def _validate_products_only(self, db: Session, items):
        """Validate all products exist and are active (NO stock validation)"""
        for item in items:
            product = self.product_repository.get(db, item.product_id)
            if not product or not product.is_active:
                raise ValueError(
                    f"Product {item.product_id} not found or inactive")

    def _reserve_stock_for_items(self, db: Session, items):
        """Reserve stock for all items"""
        for item in items:
            if not self.product_service.reserve_stock(
                    db, item.product_id, item.quantity):
                raise ValueError(
                    f"Failed to reserve stock for product {item.product_id}")

    def _restore_stock_for_items(self, db: Session, items):
        """Restore stock for all items in case of failure"""
        for item in items:
            self.product_service.update_stock(
                db, item.product_id, item.quantity)

    def _validate_and_reserve_stock_on_confirm(self, db: Session, order):
        """Validate stock availability and reserve stock when confirming order"""
        # First check if all items have sufficient stock
        insufficient_items = []
        for item in order.items:
            if not self.product_service.check_stock_availability(
                    db, item.product_id, item.quantity):
                product = self.product_repository.get(db, item.product_id)
                product_name = product.name if product else f"Product ID {item.product_id}"
                insufficient_items.append(f"{product_name} (requested: {item.quantity})")

        if insufficient_items:
            items_text = ", ".join(insufficient_items)
            raise ValueError(f"Insufficient stock for: {items_text}")

        # If validation passes, reserve stock for all items
        for item in order.items:
            if not self.product_service.reserve_stock(
                    db, item.product_id, item.quantity):
                # If reservation fails, try to restore any previously reserved stock
                # This is a fallback in case of concurrent modifications
                product = self.product_repository.get(db, item.product_id)
                product_name = product.name if product else f"Product ID {item.product_id}"
                raise ValueError(f"Failed to reserve stock for {product_name}")

        return True

    def _restore_stock_on_status_change(self, db: Session, order):
        """Restore stock when order goes back to pending or cancelled"""
        try:
            for item in order.items:
                # Restore stock (add back the quantity)
                self.product_service.update_stock(
                    db, item.product_id, item.quantity  # Add back the quantity
                )
        except Exception as e:
            print(f"Error restoring stock for order {order.id}: {str(e)}")
            # Don't raise exception to avoid breaking the status update

    def _validate_stock_availability_for_order(self, db: Session, order):
        """Validate stock availability for an order without reserving it"""
        from ..schemas.order import OrderUpdateError, ProductError

        products_with_errors = []

        for item in order.items:
            # Check if product exists and is active
            product = self.product_repository.get(db, item.product_id)
            if not product:
                products_with_errors.append(ProductError(
                    product_id=item.product_id,
                    product_name=f"Product ID {item.product_id}",
                    product_sku="N/A",
                    error_type="product_not_found",
                    error_message=f"Product with ID {item.product_id} not found"
                ))
                continue

            if not product.is_active:
                products_with_errors.append(ProductError(
                    product_id=product.id,
                    product_name=product.name,
                    product_sku=product.sku,
                    error_type="product_inactive",
                    error_message=f"Product '{product.name}' is not active"
                ))
                continue

            # Check stock availability
            if product.stock < item.quantity:
                products_with_errors.append(ProductError(
                    product_id=product.id,
                    product_name=product.name,
                    product_sku=product.sku,
                    error_type="insufficient_stock",
                    error_message=(
                        f"Insufficient stock for product '{product.name}'. "
                        f"Required: {item.quantity}, Available: {product.stock}"
                    ),
                    required_quantity=item.quantity,
                    available_quantity=product.stock
                ))

        if products_with_errors:
            return OrderUpdateError(
                order_id=order.id,
                order_number=order.order_number,
                error_type="stock_validation_failed",
                error_message=f"Order {order.order_number} failed stock validation",
                products_with_errors=products_with_errors
            )

        return None  # No errors found

    def create_order(
            self,
            db: Session,
            order_data: OrderCreate) -> OrderResponse:
        self._validate_client(db, order_data.client_id)
        self._validate_route(db, order_data.route_id)
        # LACTEOS FLOW: Only validate products exist, NO stock validation
        self._validate_products_only(db, order_data.items)
        # LACTEOS FLOW: Do NOT reserve stock at creation, only when confirmed
        # self._reserve_stock_for_items(db, order_data.items)

        # Calculate prices based on route
        self._calculate_item_prices_for_route(db, order_data)

        # Create the order (no stock reservation needed)
        order = self.order_repository.create_order_with_items(
            db, order_data=order_data)
        return self._process_order_response(order)

    def update_order_status(
            self,
            db: Session,
            order_id: int,
            status: OrderStatus) -> Optional[OrderResponse]:
        # Get current order to check status transition
        current_order = self.order_repository.get(db, order_id)
        if not current_order:
            return None

        # VALIDACIÓN DE STOCK: Si se pasa de PENDING o CANCELLED a cualquier estado que requiere stock
        stock_required_states = {OrderStatus.CONFIRMED, OrderStatus.IN_PROGRESS,
                                 OrderStatus.SHIPPED, OrderStatus.DELIVERED}
        if (current_order.status in {OrderStatus.PENDING, OrderStatus.CANCELLED} and
                status in stock_required_states):
            # Validate stock availability and reserve stock
            self._validate_and_reserve_stock_on_confirm(db, current_order)

        # RESTAURACIÓN DE STOCK: Si se vuelve a pending o cancelled desde estados que tenían stock reservado
        confirmed_states = {OrderStatus.CONFIRMED, OrderStatus.IN_PROGRESS, OrderStatus.SHIPPED, OrderStatus.DELIVERED}
        if (current_order.status in confirmed_states and
                status in {OrderStatus.PENDING, OrderStatus.CANCELLED}):
            # Restore stock (add back the reserved quantity)
            self._restore_stock_on_status_change(db, current_order)

        # Update the order status
        order = self.order_repository.update_order_status(
            db, order_id=order_id, status=status)
        if not order:
            return None
        return self._process_order_response(order)

    def cancel_order(
            self,
            db: Session,
            order_id: int) -> Optional[OrderResponse]:
        order = self.order_repository.get(db, order_id)
        if not order:
            return None

        # Only allow cancellation of pending or confirmed orders
        if order.status not in [OrderStatus.PENDING, OrderStatus.CONFIRMED]:
            raise ValueError(f"Cannot cancel order with status {order.status}")

        # RESTAURACIÓN DE STOCK: Solo restaurar si el estado tenía stock reservado
        # Pending orders don't have stock reserved, so no need to restore
        confirmed_states = {OrderStatus.CONFIRMED, OrderStatus.IN_PROGRESS, OrderStatus.SHIPPED, OrderStatus.DELIVERED}
        if order.status in confirmed_states:
            for item in order.items:
                self.product_service.update_stock(
                    db, item.product_id, item.quantity)

        updated_order = self.order_repository.update_order_status(
            db, order_id=order_id, status=OrderStatus.CANCELLED)
        return self._process_order_response(updated_order)

    def update_pending_order(
            self,
            db: Session,
            order_id: int,
            order_update: "OrderUpdate") -> Optional["OrderResponse"]:
        """
        Update a PENDING order completely (client, items, route, notes)
        LACTEOS FLOW: Allow full editing only for PENDING orders without stock validation
        """

        # Get current order
        current_order = self.order_repository.get(db, order_id)
        if not current_order:
            return None

        # Only allow full editing of PENDING orders
        if current_order.status != OrderStatus.PENDING:
            raise ValueError(
                f"Cannot edit order with status {current_order.status}. "
                "Full editing is only allowed for PENDING orders.")

        # Validate new client if provided
        if order_update.client_id is not None:
            self._validate_client(db, order_update.client_id)

        # Validate new route if provided
        if order_update.route_id is not None:
            self._validate_route(db, order_update.route_id)

        # Validate new items if provided (NO stock validation, only product existence)
        if order_update.items is not None:
            self._validate_products_only(db, order_update.items)

        # Update the order with new data
        try:
            updated_order = self.order_repository.update_pending_order_complete(
                db,
                order_id=order_id,
                order_update=order_update
            )

            if not updated_order:
                return None

            return self._process_order_response(updated_order)

        except Exception as e:
            raise ValueError(f"Failed to update order: {str(e)}")

    def _is_valid_status_transition(
            self,
            current_status: OrderStatus,
            new_status: OrderStatus) -> bool:
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

    def get_monthly_analytics_by_status(
        self,
        db: Session,
        status: OrderStatus,
        year: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> dict:
        """Get monthly analytics summary for orders with specific status"""
        from ..schemas.order import OrderAnalyticsSummary, MonthlySummary

        # Get monthly data from repository
        monthly_data_raw = self.order_repository.get_monthly_summary_by_status(
            db,
            status=status,
            year=year,
            start_date=start_date,
            end_date=end_date
        )

        # Convert to proper schema format
        month_names = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }

        monthly_summaries = []
        total_orders = 0
        total_amount = 0.0

        for data in monthly_data_raw:
            monthly_summary = MonthlySummary(
                year=data['year'],
                month=data['month'],
                month_name=month_names[data['month']],
                order_count=data['order_count'],
                total_amount=data['total_amount']
            )
            monthly_summaries.append(monthly_summary)
            total_orders += data['order_count']
            total_amount += data['total_amount']

        # Create summary response
        period_start = None
        period_end = None

        if start_date:
            period_start = start_date.strftime('%Y-%m-%d')
        if end_date:
            period_end = end_date.strftime('%Y-%m-%d')

        return OrderAnalyticsSummary(
            monthly_data=monthly_summaries,
            total_orders=total_orders,
            total_amount=total_amount,
            period_start=period_start,
            period_end=period_end
        )

    def get_status_distribution_for_month(
        self,
        db: Session,
        year: int,
        month: int
    ) -> dict:
        """Get status distribution for donut chart for a specific month"""
        from ..schemas.order import StatusDistributionSummary, StatusDistribution

        # Get raw data from repository
        status_data_raw = self.order_repository.get_status_distribution_by_month(
            db,
            year=year,
            month=month
        )

        # Status name mapping for display
        status_names = {
            'pending': 'Pendiente',
            'confirmed': 'Confirmado',
            'in_progress': 'En Proceso',
            'shipped': 'Enviado',
            'delivered': 'Entregado',
            'cancelled': 'Cancelado'
        }

        # Calculate total orders for percentage calculation
        total_orders = sum(data['count'] for data in status_data_raw)

        # Convert to proper schema format with percentages
        status_distributions = []

        for data in status_data_raw:
            status = data['status']
            count = data['count']
            percentage = (count / total_orders * 100) if total_orders > 0 else 0.0

            status_dist = StatusDistribution(
                status=status,
                status_name=status_names.get(status, status.title()),
                count=count,
                percentage=round(percentage, 1)
            )
            status_distributions.append(status_dist)

        # Create month name
        month_names = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }

        period_name = f"{month_names.get(month, month)} {year}"

        return StatusDistributionSummary(
            status_data=status_distributions,
            total_orders=total_orders,
            month=month,
            year=year,
            period_name=period_name
        )

    def _calculate_item_prices_for_route(self, db: Session, order_data: OrderCreate):
        """Calculate item prices based on route, using route-specific prices or default product prices"""
        for item in order_data.items:
            # Get the appropriate price for this product and route
            price = self.product_service.get_product_price_for_route(
                db, item.product_id, order_data.route_id
            )
            # Update the unit price in the item
            item.unit_price = price

    def batch_update_status(
        self,
        db: Session,
        order_ids: List[int],
        new_status: OrderStatus,
        notes: Optional[str] = None
    ) -> dict:
        """Update status for multiple orders with proper stock management and granular error handling"""
        from ..schemas.order import BatchOrderUpdateResponse

        success_orders = []
        failed_orders = []
        success_details = []
        failed_details = []

        for order_id in order_ids:
            self._process_single_order_update(
                db, order_id, new_status, notes,
                success_orders, failed_orders, success_details, failed_details
            )

        return BatchOrderUpdateResponse(
            updated_count=len(success_orders),
            failed_count=len(failed_orders),
            total_orders=len(order_ids),
            status=new_status,
            failed_orders=failed_orders,
            success_orders=success_orders,
            success_details=success_details,
            failed_details=failed_details
        )

    def _process_single_order_update(self, db, order_id, new_status, notes,
                                     success_orders, failed_orders, success_details, failed_details):
        """Process a single order update"""
        try:
            # Get the order first to check if it exists
            order = self.order_repository.get(db, order_id)
            if not order:
                self._add_order_error(order_id, None, "order_not_found",
                                      f"Order {order_id} not found", failed_orders, failed_details)
                return

            # Check if this is a stock-requiring transition
            if self._requires_stock_validation(order, new_status):
                stock_error = self._validate_stock_availability_for_order(db, order)
                if stock_error:
                    failed_orders.append(order_id)
                    failed_details.append(stock_error)
                    return

            # Use the existing update_order_status method to ensure consistent stock management
            updated_order = self.update_order_status(db, order_id, new_status)

            if updated_order:
                self._handle_successful_update(db, order, notes, order_id,
                                               success_orders, success_details)
            else:
                self._add_order_error(order_id, order.order_number, "update_failed",
                                      f"Failed to update order {order_id} status",
                                      failed_orders, failed_details)

        except Exception as e:
            # Log the error (you might want to add proper logging here)
            print(f"Error updating order {order_id}: {str(e)}")
            order_number = order.order_number if 'order' in locals() and order else None
            self._add_order_error(order_id, order_number, "unexpected_error", str(e),
                                  failed_orders, failed_details)

    def _requires_stock_validation(self, order, new_status):
        """Check if order status transition requires stock validation"""
        # Estados que requieren validación de stock
        stock_required_states = {OrderStatus.CONFIRMED, OrderStatus.IN_PROGRESS,
                                 OrderStatus.SHIPPED, OrderStatus.DELIVERED}
        # Validar stock cuando se pasa de PENDING o CANCELLED a estados que requieren stock
        return (order.status in {OrderStatus.PENDING, OrderStatus.CANCELLED} and
                new_status in stock_required_states)

    def _handle_successful_update(self, db, order, notes, order_id, success_orders, success_details):
        """Handle successful order update"""
        from ..schemas.order import OrderUpdateSuccess
        # Update notes if provided
        if notes:
            self.order_repository.update(
                db,
                db_obj=order,
                obj_in={"notes": notes}
            )

        # Get product details for successful orders
        products_updated = self._get_products_updated(db, order)

        success_orders.append(order_id)
        success_details.append(OrderUpdateSuccess(
            order_id=order.id,
            order_number=order.order_number,
            products_updated=products_updated
        ))

    def _get_products_updated(self, db, order):
        """Get product details for updated order"""
        products_updated = []
        for item in order.items:
            product = self.product_repository.get(db, item.product_id)
            if product:
                products_updated.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "product_sku": product.sku,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price
                })
        return products_updated

    def _add_order_error(self, order_id, order_number, error_type, error_message,
                         failed_orders, failed_details):
        """Add order error to failed lists"""
        from ..schemas.order import OrderUpdateError
        failed_orders.append(order_id)
        failed_details.append(OrderUpdateError(
            order_id=order_id,
            order_number=order_number,
            error_type=error_type,
            error_message=error_message,
            products_with_errors=[]
        ))
