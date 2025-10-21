from typing import List, Optional, Union
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
from ...schemas.order import (
    OrderCreate, OrderUpdate, OrderResponse, OrderItemCreate,
    OrderAnalyticsSummary, StatusDistributionSummary,
    BatchOrderUpdateRequest, BatchOrderUpdateResponse
)
from ...schemas.pagination import PaginatedResponse
from ...services.order_service import OrderService
from ...services.compact_receipt_generator import CompactReceiptGenerator
from ...services.orders_report_generator import OrdersReportGenerator
from ...services.settings_service import SettingsService
from ...models.order import OrderStatus
from ..dependencies import get_order_service, get_settings_service
from .auth import get_current_active_user, get_tenant_db
from ...models.user import User
from ...utils.date_filters import create_date_range_utc, validate_date_range
from ...middleware import get_request_timezone
from ...utils.permissions import can_create_orders, can_view_orders, can_update_delivery_status, can_update_stock_required_status

router = APIRouter(prefix="/orders", tags=["orders"])


# No additional schemas needed - using existing ones


@router.post("/", response_model=OrderResponse,
             status_code=status.HTTP_201_CREATED)
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new order (requires sales+ role)"""
    # Verificar permisos
    if not can_create_orders(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para crear pedidos. Se requiere rol de Vendedor o superior."
        )

    try:
        return order_service.create_order(db, order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/",
            response_model=Union[List[OrderResponse],
                                 PaginatedResponse[OrderResponse]])
def get_orders(
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[str] = Query(
            None,
            description="Filter by order status"),
        route_id: Optional[int] = Query(
            None,
            description="Filter by route ID"),
        date_from: Optional[date] = Query(
            None,
            description="Filter orders from this date (YYYY-MM-DD)"),
        date_to: Optional[date] = Query(
            None,
            description="Filter orders to this date (YYYY-MM-DD)"),
        search: Optional[str] = Query(
            None,
            description="Search by order number or client name"),
        paginated: bool = Query(
            True,
            description="Return paginated response with metadata"),
        db: Session = Depends(get_tenant_db),
        order_service: OrderService = Depends(get_order_service),
        current_user: User = Depends(get_current_active_user),
        request: Request = None):
    """Get all orders with optional filters (requires view orders permission)

    Filters:
    - status_filter: Filter by order status (pending, confirmed, in_progress, shipped, delivered, cancelled)
    - route_id: Filter by specific route ID
    - date_from: Show orders from this date onwards (inclusive)
    - date_to: Show orders up to this date (inclusive)
    - search: Search by order number or client name (case-insensitive partial matching)
    - paginated: Return paginated response with metadata (default: True)

    Response:
    - If paginated=True: Returns PaginatedResponse with items and pagination metadata
    - If paginated=False: Returns List[OrderResponse] for backward compatibility
    """
    # Verificar permisos
    if not can_view_orders(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver pedidos."
        )

    # Validate date range
    validate_date_range(date_from, date_to)
    
    # Get client timezone and convert date filters to UTC
    client_timezone = get_request_timezone(request) if request else None
    if client_timezone:
        date_from_utc, date_to_utc = create_date_range_utc(date_from, date_to, client_timezone)
    else:
        # Fallback to original dates if no timezone available
        date_from_utc = date_from
        date_to_utc = date_to

    # Convert status filter to enum if provided
    status_enum = None
    if status_filter:
        try:
            status_enum = OrderStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status_filter}. Valid values are: {', '.join([s.value for s in OrderStatus])}"
            )

    # Choose response format based on paginated parameter
    if paginated:
        # Use paginated response with full metadata
        if any([status_enum, route_id, date_from_utc, date_to_utc, search]):
            return order_service.get_orders_paginated(
                db,
                skip=skip,
                limit=limit,
                status=status_enum,
                route_id=route_id,
                date_from=date_from_utc,
                date_to=date_to_utc,
                search=search
            )
        else:
            # No filters but paginated response
            return order_service.get_orders_paginated(
                db, skip=skip, limit=limit)
    else:
        # Backward compatibility: return simple list
        if any([status_enum, route_id, date_from_utc, date_to_utc, search]):
            return order_service.get_orders_with_filters(
                db,
                skip=skip,
                limit=limit,
                status=status_enum,
                route_id=route_id,
                date_from=date_from_utc,
                date_to=date_to_utc,
                search=search
            )
        else:
            return order_service.get_orders(db, skip=skip, limit=limit)


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: int,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific order by ID (requires authentication)"""
    order = order_service.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.put("/bulk-status", response_model=BatchOrderUpdateResponse)
def batch_update_order_status(
    batch_request: BatchOrderUpdateRequest,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
    """Update status for multiple orders (requires authentication)"""
    try:
        # Validación de permisos según el estado
        if batch_request.status == OrderStatus.DELIVERED:
            if not can_update_delivery_status(current_user):
                raise HTTPException(
                    status_code=403,
                    detail="No tienes permisos para marcar pedidos como entregados. Se requiere rol de Repartidor o superior."
                )
        elif batch_request.status in [OrderStatus.CONFIRMED, OrderStatus.IN_PROGRESS, OrderStatus.SHIPPED]:
            # Estados que requieren validación de stock
            if not can_update_stock_required_status(current_user):
                raise HTTPException(
                    status_code=403,
                    detail="No tienes permisos para cambiar a estados que requieren validación de stock. Se requiere rol de Vendedor o superior."
                )
        else:
            # Para otros cambios de estado (pending, cancelled), requiere permisos básicos
            if not can_create_orders(current_user):
                raise HTTPException(
                    status_code=403,
                    detail="No tienes permisos para cambiar el estado de pedidos. Se requiere rol de Vendedor o superior."
                )

        # Perform batch update
        result = order_service.batch_update_status(
            db,
            batch_request.order_ids,
            batch_request.status,
            batch_request.notes
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating orders: {str(e)}")


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an order

    Behavior depends on order status:
    - PENDING orders: Complete update allowed (client, items, route, notes)
    - Other status: Only basic fields (route, notes, status)
    """
    try:
        if not can_create_orders(current_user):
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions to edit orders")

        # Get current order to check status
        current_order = order_service.get_order(db, order_id)
        if not current_order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Check if this is a full update request (has items)
        is_full_update = order_update.items is not None

        # If order is PENDING and we have full update data, allow complete editing
        if current_order.status == OrderStatus.PENDING and is_full_update:
            # Full update for PENDING orders
            order = order_service.update_pending_order(db, order_id, order_update)
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
            return order

        # Otherwise, only basic updates
        else:
            # Handle status update
            if order_update.status is not None:
                order = order_service.update_order_status(db, order_id, order_update.status)
                if not order:
                    raise HTTPException(status_code=404, detail="Order not found")
                return order

            # For other basic field updates (route, notes) on non-PENDING orders
            # We can add this functionality later if needed
            else:
                raise HTTPException(
                    status_code=400,
                    detail="For PENDING orders, provide 'items' for complete editing. For other orders, use status updates.")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Status updates handled by existing endpoint PUT /{order_id}/status/{new_status}


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: int,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an order (requires authentication)"""
    order = order_service.cancel_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return None


@router.post("/{order_id}/items", response_model=OrderResponse)
def add_order_item(
    order_id: int,
    item: OrderItemCreate,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
    """Add an item to an order (requires authentication)"""
    try:
        # This method needs to be implemented in the service
        raise HTTPException(status_code=501,
                            detail="Add order item not yet implemented")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{order_id}/items/{item_id}", response_model=OrderResponse)
def remove_order_item(
    order_id: int,
    item_id: int,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
    """Remove an item from an order (requires authentication)"""
    try:
        # This method needs to be implemented in the service
        raise HTTPException(status_code=501,
                            detail="Remove order item not yet implemented")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{order_id}/status/{new_status}", response_model=OrderResponse)
def update_order_status(
    order_id: int,
    new_status: str,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
    """Update order status (requires appropriate permissions)"""
    try:
        status_enum = OrderStatus(new_status)

        # Validación de permisos según el estado
        if status_enum == OrderStatus.DELIVERED:
            if not can_update_delivery_status(current_user):
                raise HTTPException(
                    status_code=403,
                    detail="No tienes permisos para marcar pedidos como entregados. Se requiere rol de Repartidor o superior."
                )
        elif status_enum in [OrderStatus.CONFIRMED, OrderStatus.IN_PROGRESS, OrderStatus.SHIPPED]:
            # Estados que requieren validación de stock
            if not can_update_stock_required_status(current_user):
                raise HTTPException(
                    status_code=403,
                    detail="No tienes permisos para cambiar a estados que requieren validación de stock. Se requiere rol de Vendedor o superior."
                )
        else:
            # Para otros cambios de estado (pending, cancelled), requiere permisos básicos
            if not can_create_orders(current_user):
                raise HTTPException(
                    status_code=403,
                    detail="No tienes permisos para cambiar el estado de pedidos. Se requiere rol de Vendedor o superior."
                )

        order = order_service.update_order_status(db, order_id, status_enum)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/client/{client_id}", response_model=List[OrderResponse])
def get_orders_by_client(
    client_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get orders by client ID (requires authentication)"""
    orders = order_service.get_orders_by_client(
        db, client_id, skip=skip, limit=limit)
    return orders


# ===== COMPROBANTES DE ÓRDENES =====

@router.get("/{order_id}/receipt", response_class=StreamingResponse)
def download_order_receipt(
    order_id: int,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    settings_service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """Download order receipt/voucher PDF (requires authentication)"""
    try:
        # Get order
        order = order_service.get_order(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Get company settings
        settings = settings_service.get_company_settings(db)
        if not settings:
            raise HTTPException(
                status_code=404,
                detail="Company settings not found. Please configure company information first."
            )

        # Create professional receipt generator
        receipt_generator = CompactReceiptGenerator()

        # Get order object for PDF generation
        from ...repositories.order_repository import OrderRepository
        order_repo = OrderRepository()
        order_obj = order_repo.get(db, order_id)

        if not order_obj:
            raise HTTPException(status_code=404, detail="Order not found")

        # Get client timezone and pass to PDF generator
        client_timezone = get_request_timezone(request) if request else None
        
        # Generate PDF buffer with company settings and client timezone
        pdf_buffer = receipt_generator.generate_receipt_buffer(
            order_obj, settings, client_timezone)

        # Set filename
        filename = f"comprobante_pedido_{order_obj.order_number}.pdf"

        # Return as streaming response
        return StreamingResponse(
            BytesIO(pdf_buffer.getvalue()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Error generating receipt: {str(e)}")


@router.get("/{order_id}/receipt/preview", response_class=StreamingResponse)
def preview_order_receipt(
    order_id: int,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    settings_service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """Preview order receipt PDF in browser (requires authentication)"""
    try:
        # Get order
        order = order_service.get_order(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Get company settings
        settings = settings_service.get_company_settings(db)
        if not settings:
            raise HTTPException(
                status_code=404,
                detail="Company settings not found. Please configure company information first."
            )

        # Create professional receipt generator
        receipt_generator = CompactReceiptGenerator()

        # Get order object for PDF generation
        from ...repositories.order_repository import OrderRepository
        order_repo = OrderRepository()
        order_obj = order_repo.get(db, order_id)

        if not order_obj:
            raise HTTPException(status_code=404, detail="Order not found")

        # Get client timezone and pass to PDF generator
        client_timezone = get_request_timezone(request) if request else None
        
        # Generate PDF buffer with company settings and client timezone
        pdf_buffer = receipt_generator.generate_receipt_buffer(
            order_obj, settings, client_timezone)

        # Return as inline PDF (for preview in browser)
        return StreamingResponse(
            BytesIO(pdf_buffer.getvalue()),
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Error generating receipt: {str(e)}")


@router.post("/{order_id}/receipt/generate")
def generate_order_receipt_file(
    order_id: int,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    settings_service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """Generate and save order receipt PDF file (requires authentication)"""
    try:
        # Get order
        order = order_service.get_order(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Get company settings
        settings = settings_service.get_company_settings(db)
        if not settings:
            raise HTTPException(
                status_code=404,
                detail="Company settings not found. Please configure company information first."
            )

        # Create professional receipt generator
        receipt_generator = CompactReceiptGenerator()

        # Get order object for PDF generation
        from ...repositories.order_repository import OrderRepository
        order_repo = OrderRepository()
        order_obj = order_repo.get(db, order_id)

        if not order_obj:
            raise HTTPException(status_code=404, detail="Order not found")

        # Create receipts directory if it doesn't exist
        import os
        receipts_dir = "receipts"
        os.makedirs(receipts_dir, exist_ok=True)

        # Get client timezone and pass to PDF generator
        client_timezone = get_request_timezone(request) if request else None
        
        # Generate filename
        filename = f"comprobante_{order_obj.order_number}_{order_obj.created_at.strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path = os.path.join(receipts_dir, filename)

        # Generate PDF file with company settings and client timezone
        receipt_generator.generate_order_receipt(
            order_obj, settings, file_path, client_timezone)

        return {
            "message": "Receipt generated successfully",
            "file_path": file_path,
            "order_id": order_id,
            "order_number": order_obj.order_number
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500,
                            detail=f"Error generating receipt: {str(e)}")


# ===== REPORTE DE ÓRDENES EN PDF =====

# Helper functions for complex report generation
def _validate_report_permissions(current_user: User):
    """Validate user permissions for report generation"""
    if not can_view_orders(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para generar reportes de pedidos."
        )


def _validate_date_range(date_from: Optional[date], date_to: Optional[date]):
    """Validate date range parameters"""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=400,
            detail="date_from cannot be later than date_to"
        )


def _parse_status_filter(
        status_filter: Optional[str]) -> Optional[OrderStatus]:
    """Parse and validate status filter"""
    if not status_filter:
        return None

    try:
        return OrderStatus(status_filter)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {status_filter}. Valid values are: {', '.join([s.value for s in OrderStatus])}"
        )


def _get_filtered_orders(order_service, db, status_enum,
                         route_id, date_from, date_to, search):
    """Get orders with applied filters"""
    orders = order_service.get_orders_with_filters(
        db,
        skip=0,
        limit=10000,  # Large limit to get all orders
        status=status_enum,
        route_id=route_id,
        date_from=date_from,
        date_to=date_to,
        search=search
    )

    if not orders:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron órdenes con los filtros especificados")

    return orders


def _get_company_settings(settings_service, db):
    """Get company settings for report"""
    settings = settings_service.get_company_settings(db)
    if not settings:
        raise HTTPException(
            status_code=404,
            detail="Company settings not found. Please configure company information first."
        )
    return settings


def _get_raw_orders(db, orders):
    """Convert order responses to raw order objects for PDF generation"""
    from ...repositories.order_repository import OrderRepository
    order_repo = OrderRepository()

    order_ids = [order.id for order in orders]
    raw_orders = []
    for order_id in order_ids:
        raw_order = order_repo.get(db, order_id)
        if raw_order:
            raw_orders.append(raw_order)

    if not raw_orders:
        raise HTTPException(status_code=404, detail="Orders not found")

    return raw_orders


def _generate_report_title(status_filter, route_id, date_from, date_to, db):
    """Generate report title based on filters"""
    title_parts = ["Reporte de Órdenes"]

    # Add route name if filtered by route
    if route_id:
        from ...repositories.route_repository import RouteRepository
        route_repo = RouteRepository()
        route = route_repo.get(db, route_id)
        if route:
            title_parts.append(f"- Ruta: {route.name}")

    # Add status filter
    if status_filter:
        status_names = {
            'pending': 'Pendientes',
            'confirmed': 'Confirmadas',
            'in_progress': 'En Proceso',
            'shipped': 'Enviadas',
            'delivered': 'Entregadas',
            'cancelled': 'Canceladas'
        }
        title_parts.append(
            f"- {status_names.get(status_filter, status_filter.title())}")

    # Add date range
    if date_from or date_to:
        if date_from and date_to:
            title_parts.append(
                f"({date_from.strftime('%d/%m/%Y')} - {date_to.strftime('%d/%m/%Y')})")
        elif date_from:
            title_parts.append(f"(desde {date_from.strftime('%d/%m/%Y')})")
        elif date_to:
            title_parts.append(f"(hasta {date_to.strftime('%d/%m/%Y')})")

    return " ".join(title_parts)


@router.get("/report/pdf", response_class=StreamingResponse)
def download_orders_report_pdf(
        status_filter: Optional[str] = Query(
            None,
            description="Filter by order status"),
        route_id: Optional[int] = Query(
            None,
            description="Filter by route ID"),
        date_from: Optional[date] = Query(
            None,
            description="Filter orders from this date (YYYY-MM-DD)"),
        date_to: Optional[date] = Query(
            None,
            description="Filter orders to this date (YYYY-MM-DD)"),
        search: Optional[str] = Query(
            None,
            description="Search by order number or client name"),
        db: Session = Depends(get_tenant_db),
        order_service: OrderService = Depends(get_order_service),
        settings_service: SettingsService = Depends(get_settings_service),
        current_user: User = Depends(get_current_active_user),
        request: Request = None):
    """Download orders report PDF with filters

    Genera un PDF con múltiples órdenes agrupadas por cliente.
    El PDF incluye:
    - Encabezado con logo, nombre y teléfono de la empresa
    - Órdenes organizadas por cliente con información compacta
    - Solo nombre, número, dirección del cliente
    - Por cada orden: número, fecha, detalle de productos, total
    - Resumen general por estado

    Filters (same as get orders endpoint):
    - status_filter: Filter by order status (pending, confirmed, in_progress, shipped, delivered, cancelled)
    - route_id: Filter by specific route ID
    - date_from: Show orders from this date onwards (inclusive)
    - date_to: Show orders up to this date (inclusive)
    - search: Search by order number or client name (case-insensitive partial matching)
    """
    try:
        _validate_report_permissions(current_user)
        _validate_date_range(date_from, date_to)

        status_enum = _parse_status_filter(status_filter)

        # Get client timezone and convert date filters to UTC
        client_timezone = get_request_timezone(request) if request else None
        if client_timezone:
            date_from_utc, date_to_utc = create_date_range_utc(date_from, date_to, client_timezone)
        else:
            # Fallback to original dates if no timezone available
            date_from_utc = date_from
            date_to_utc = date_to

        orders = _get_filtered_orders(
            order_service,
            db,
            status_enum,
            route_id,
            date_from_utc,
            date_to_utc,
            search)
        settings = _get_company_settings(settings_service, db)
        raw_orders = _get_raw_orders(db, orders)

        report_title = _generate_report_title(
            status_filter, route_id, date_from, date_to, db)

        # Get client timezone and pass to PDF generator
        client_timezone = get_request_timezone(request) if request else None

        # Generate PDF buffer
        report_generator = OrdersReportGenerator()
        pdf_buffer = report_generator.generate_report_buffer(
            raw_orders, settings, report_title, client_timezone)

        # Set filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reporte_ordenes_{timestamp}.pdf"

        # Return as streaming response
        return StreamingResponse(
            BytesIO(pdf_buffer.getvalue()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        # Re-raise HTTPExceptions (like 404 for no orders found)
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error generating orders report: {str(e)}")


# ===== ENDPOINTS DE ANALYTICS =====

@router.get("/analytics/monthly-summary", response_model=OrderAnalyticsSummary)
def get_monthly_orders_analytics(
        status_filter: str = Query(
            ...,
            description="Filter by order status (required)"),
        year: Optional[int] = Query(
            None,
            description="Filter by specific year"),
        start_date: Optional[date] = Query(
            None,
            description="Start date for analysis (YYYY-MM-DD)"),
        end_date: Optional[date] = Query(
            None,
            description="End date for analysis (YYYY-MM-DD)"),
        db: Session = Depends(get_tenant_db),
        order_service: OrderService = Depends(get_order_service),
        current_user: User = Depends(get_current_active_user)):
    """Get monthly summary analytics for orders by status

    Returns aggregated data showing order count and total amount by month.
    Perfect for creating bar charts or line graphs showing monthly trends.

    Parameters:
    - status_filter: Order status (pending, confirmed, in_progress, shipped, delivered, cancelled)
    - year: Optional filter by specific year
    - start_date: Optional start date for analysis period
    - end_date: Optional end date for analysis period

    Response includes:
    - monthly_data: List of monthly summaries with year, month, count, and total amount
    - total_orders: Sum of all orders in the period
    - total_amount: Sum of all amounts in the period
    - period_start/end: Date range analyzed
    """
    try:
        # Verify permissions
        if not can_view_orders(current_user):
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para ver analíticos de pedidos."
            )

        # Validate date range
        if start_date and end_date and start_date > end_date:
            raise HTTPException(
                status_code=400,
                detail="start_date cannot be later than end_date"
            )

        # Parse and validate status
        try:
            status_enum = OrderStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status_filter}. Valid values are: {', '.join([s.value for s in OrderStatus])}"
            )

        # Get analytics data
        analytics_data = order_service.get_monthly_analytics_by_status(
            db,
            status=status_enum,
            year=year,
            start_date=start_date,
            end_date=end_date
        )

        return analytics_data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting monthly analytics: {str(e)}")


@router.get("/analytics/status-distribution", response_model=StatusDistributionSummary)
def get_status_distribution(
        year: Optional[int] = Query(
            None,
            description="Year for analysis (defaults to current year)"),
        month: Optional[int] = Query(
            None,
            description="Month for analysis (1-12, defaults to current month)"),
        db: Session = Depends(get_tenant_db),
        order_service: OrderService = Depends(get_order_service),
        current_user: User = Depends(get_current_active_user)):
    """Get order status distribution for donut chart

    Returns the count and percentage of orders by status for a specific month.
    Perfect for creating donut charts showing order status distribution.

    Parameters:
    - year: Year for analysis (optional, defaults to current year)
    - month: Month for analysis (1-12, optional, defaults to current month)

    Response includes:
    - status_data: List with each status, its name, count, and percentage
    - total_orders: Total orders in the period
    - month/year: Period analyzed
    - period_name: Human-readable period name

    Example response for donut chart:
    {
      "status_data": [
        {"status": "delivered", "status_name": "Entregado", "count": 15, "percentage": 50.0},
        {"status": "pending", "status_name": "Pendiente", "count": 10, "percentage": 33.3},
        {"status": "cancelled", "status_name": "Cancelado", "count": 5, "percentage": 16.7}
      ],
      "total_orders": 30,
      "month": 9,
      "year": 2025,
      "period_name": "Septiembre 2025"
    }
    """
    try:
        # Verify permissions
        if not can_view_orders(current_user):
            raise HTTPException(
                status_code=403,
                detail="No tienes permisos para ver analíticos de pedidos."
            )

        # Use current month/year if not provided
        from datetime import datetime
        now = datetime.now()

        analysis_year = year if year is not None else now.year
        analysis_month = month if month is not None else now.month

        # Validate month range
        if analysis_month < 1 or analysis_month > 12:
            raise HTTPException(
                status_code=400,
                detail="Month must be between 1 and 12"
            )

        # Get status distribution data
        distribution_data = order_service.get_status_distribution_for_month(
            db,
            year=analysis_year,
            month=analysis_month
        )

        return distribution_data

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting status distribution: {str(e)}")
