from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
from ...database import get_db
from ...schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderItemCreate
from ...schemas.invoice import CompanyInfo
from ...services.order_service import OrderService
from ...services.receipt_generator import ReceiptGenerator
from ...models.order import OrderStatus
from ..dependencies import get_order_service
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


@router.get("/", response_model=List[OrderResponse])
def get_orders(
    skip: int = 0,
    limit: int = 100,
    status_filter: str = None,
    db: Session = Depends(get_tenant_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get all orders (requires view orders permission)"""
    # Verificar permisos
    if not can_view_orders(current_user):
        raise HTTPException(
            status_code=403, 
            detail="No tienes permisos para ver pedidos."
        )
    
    if status_filter:
        try:
            status_enum = OrderStatus(status_filter)
            return order_service.get_orders_by_status(db, status_enum, skip=skip, limit=limit)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}")
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
    current_user: User = Depends(get_current_active_user)
):
    """Download order receipt/voucher PDF (requires authentication)"""
    try:
        # Get order
        order = order_service.get_order(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Create receipt generator
        receipt_generator = ReceiptGenerator()
        
        # Company info (should be configurable)
        company_info = CompanyInfo(
            name="Smart Orders Guatemala",
            address="Zona 10, Ciudad de Guatemala, Guatemala",
            phone="+502 2222-3333",
            email="comprobantes@smartorders.gt",
            nit="12345678-9"
        )
        
        # Get order object for PDF generation
        from ...repositories.order_repository import OrderRepository
        order_repo = OrderRepository()
        order_obj = order_repo.get(db, order_id)
        
        if not order_obj:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Generate PDF buffer
        pdf_buffer = receipt_generator.generate_receipt_buffer(order_obj, company_info)
        
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
    current_user: User = Depends(get_current_active_user)
):
    """Preview order receipt PDF in browser (requires authentication)"""
    try:
        # Get order
        order = order_service.get_order(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Create receipt generator
        receipt_generator = ReceiptGenerator()
        
        # Company info
        company_info = CompanyInfo(
            name="Smart Orders Guatemala",
            address="Zona 10, Ciudad de Guatemala, Guatemala", 
            phone="+502 2222-3333",
            email="comprobantes@smartorders.gt",
            nit="12345678-9"
        )
        
        # Get order object for PDF generation
        from ...repositories.order_repository import OrderRepository
        order_repo = OrderRepository()
        order_obj = order_repo.get(db, order_id)
        
        if not order_obj:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Generate PDF buffer
        pdf_buffer = receipt_generator.generate_receipt_buffer(order_obj, company_info)
        
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
    current_user: User = Depends(get_current_active_user)
):
    """Generate and save order receipt PDF file (requires authentication)"""
    try:
        # Get order
        order = order_service.get_order(db, order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Create receipt generator
        receipt_generator = ReceiptGenerator()
        
        # Company info
        company_info = CompanyInfo(
            name="Smart Orders Guatemala",
            address="Zona 10, Ciudad de Guatemala, Guatemala",
            phone="+502 2222-3333", 
            email="comprobantes@smartorders.gt",
            nit="12345678-9"
        )
        
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
        
        # Generate PDF file
        receipt_generator.generate_order_receipt(order_obj, company_info, file_path)
        
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