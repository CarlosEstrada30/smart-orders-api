from typing import List, Optional, Union
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
from ...database import get_db
from ...schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderItemCreate
from ...schemas.pagination import PaginatedResponse
from ...schemas.invoice import CompanyInfo
from ...services.order_service import OrderService
from ...services.receipt_generator import ReceiptGenerator
from ...services.compact_receipt_generator import CompactReceiptGenerator
from ...services.orders_report_generator import OrdersReportGenerator
from ...services.settings_service import SettingsService
from ...models.order import OrderStatus
from ..dependencies import get_order_service, get_settings_service
from .auth import get_current_active_user, get_tenant_db
from ...models.user import User
from ...utils.permissions import can_create_orders, can_view_orders, can_update_delivery_status

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
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


@router.get("/", response_model=Union[List[OrderResponse], PaginatedResponse[OrderResponse]])
def get_orders(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = Query(None, description="Filter by order status"),
    route_id: Optional[int] = Query(None, description="Filter by route ID"),
    date_from: Optional[date] = Query(None, description="Filter orders from this date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Filter orders to this date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search by order number or client name"),
    paginated: bool = Query(True, description="Return paginated response with metadata"),
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
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
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=400, 
            detail="date_from cannot be later than date_to"
        )
    
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
        if any([status_enum, route_id, date_from, date_to, search]):
            return order_service.get_orders_paginated(
                db, 
                skip=skip, 
                limit=limit,
                status=status_enum,
                route_id=route_id,
                date_from=date_from,
                date_to=date_to,
                search=search
            )
        else:
            # No filters but paginated response
            return order_service.get_orders_paginated(db, skip=skip, limit=limit)
    else:
        # Backward compatibility: return simple list
        if any([status_enum, route_id, date_from, date_to, search]):
            return order_service.get_orders_with_filters(
                db, 
                skip=skip, 
                limit=limit,
                status=status_enum,
                route_id=route_id,
                date_from=date_from,
                date_to=date_to,
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


@router.put("/{order_id}", response_model=OrderResponse)
def update_order(
    order_id: int,
    order_update: OrderUpdate,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
    """Update an order (requires authentication)"""
    try:
        # For now, only status updates are supported
        if order_update.status is not None:
            order = order_service.update_order_status(db, order_id, order_update.status)
            if not order:
                raise HTTPException(status_code=404, detail="Order not found")
            return order
        else:
            raise HTTPException(status_code=400, detail="Only status updates are currently supported")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
        raise HTTPException(status_code=501, detail="Add order item not yet implemented")
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
        raise HTTPException(status_code=501, detail="Remove order item not yet implemented")
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
        
        # Validación especial para repartidores
        if status_enum == OrderStatus.DELIVERED:
            if not can_update_delivery_status(current_user):
                raise HTTPException(
                    status_code=403, 
                    detail="No tienes permisos para marcar pedidos como entregados. Se requiere rol de Repartidor o superior."
                )
        else:
            # Para otros cambios de estado, requiere permisos de gestión
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
    orders = order_service.get_orders_by_client(db, client_id, skip=skip, limit=limit)
    return orders


# ===== COMPROBANTES DE ÓRDENES =====

@router.get("/{order_id}/receipt", response_class=StreamingResponse)
def download_order_receipt(
    order_id: int,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    settings_service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(get_current_active_user)
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
        
        # Generate PDF buffer with company settings
        pdf_buffer = receipt_generator.generate_receipt_buffer(order_obj, settings)
        
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
        raise HTTPException(status_code=500, detail=f"Error generating receipt: {str(e)}")


@router.get("/{order_id}/receipt/preview", response_class=StreamingResponse)
def preview_order_receipt(
    order_id: int,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    settings_service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(get_current_active_user)
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
        
        # Generate PDF buffer with company settings
        pdf_buffer = receipt_generator.generate_receipt_buffer(order_obj, settings)
        
        # Return as inline PDF (for preview in browser)
        return StreamingResponse(
            BytesIO(pdf_buffer.getvalue()),
            media_type="application/pdf",
            headers={"Content-Disposition": "inline"}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating receipt: {str(e)}")


@router.post("/{order_id}/receipt/generate")
def generate_order_receipt_file(
    order_id: int,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    settings_service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(get_current_active_user)
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
        
        # Generate filename
        filename = f"comprobante_{order_obj.order_number}_{order_obj.created_at.strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path = os.path.join(receipts_dir, filename)
        
        # Generate PDF file with company settings
        receipt_generator.generate_order_receipt(order_obj, settings, file_path)
        
        return {
            "message": "Receipt generated successfully",
            "file_path": file_path,
            "order_id": order_id,
            "order_number": order_obj.order_number
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating receipt: {str(e)}")


# ===== REPORTE DE ÓRDENES EN PDF =====

@router.get("/report/pdf", response_class=StreamingResponse)
def download_orders_report_pdf(
    status_filter: Optional[str] = Query(None, description="Filter by order status"),
    route_id: Optional[int] = Query(None, description="Filter by route ID"),
    date_from: Optional[date] = Query(None, description="Filter orders from this date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Filter orders to this date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search by order number or client name"),
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    settings_service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(get_current_active_user)
):
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
        # Verificar permisos
        if not can_view_orders(current_user):
            raise HTTPException(
                status_code=403, 
                detail="No tienes permisos para generar reportes de pedidos."
            )
        
        # Validate date range
        if date_from and date_to and date_from > date_to:
            raise HTTPException(
                status_code=400, 
                detail="date_from cannot be later than date_to"
            )
        
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
        
        # Get filtered orders (without pagination to get all results)
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
                detail="No se encontraron órdenes con los filtros especificados"
            )
        
        # Get company settings
        settings = settings_service.get_company_settings(db)
        if not settings:
            raise HTTPException(
                status_code=404, 
                detail="Company settings not found. Please configure company information first."
            )
        
        # Create report generator
        report_generator = OrdersReportGenerator()
        
        # Get order objects for PDF generation (need the raw objects, not processed responses)
        from ...repositories.order_repository import OrderRepository
        order_repo = OrderRepository()
        
        # Get raw order objects using their IDs
        order_ids = [order.id for order in orders]
        raw_orders = []
        for order_id in order_ids:
            raw_order = order_repo.get(db, order_id)
            if raw_order:
                raw_orders.append(raw_order)
        
        if not raw_orders:
            raise HTTPException(status_code=404, detail="Orders not found")
        
        # Generate title based on filters
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
            title_parts.append(f"- {status_names.get(status_filter, status_filter.title())}")
        
        # Add date range
        if date_from or date_to:
            if date_from and date_to:
                title_parts.append(f"({date_from.strftime('%d/%m/%Y')} - {date_to.strftime('%d/%m/%Y')})")
            elif date_from:
                title_parts.append(f"(desde {date_from.strftime('%d/%m/%Y')})")
            elif date_to:
                title_parts.append(f"(hasta {date_to.strftime('%d/%m/%Y')})")
        
        report_title = " ".join(title_parts)
        
        # Generate PDF buffer
        pdf_buffer = report_generator.generate_report_buffer(raw_orders, settings, report_title)
        
        # Set filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"reporte_ordenes_{timestamp}.pdf"
        
        # Return as streaming response
        return StreamingResponse(
            BytesIO(pdf_buffer.getvalue()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating orders report: {str(e)}") 