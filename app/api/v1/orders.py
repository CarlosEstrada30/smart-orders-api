from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ...database import get_db
from ...schemas.order import OrderCreate, OrderUpdate, OrderResponse, OrderItemCreate
from ...services.order_service import OrderService
from ...models.order import OrderStatus
from ..dependencies import get_order_service
from .auth import get_current_active_user
from ...models.user import User

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new order (requires authentication)"""
    try:
        return order_service.create_order(db, order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[OrderResponse])
def get_orders(
    skip: int = 0,
    limit: int = 100,
    status_filter: str = None,
    db: Session = Depends(get_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get all orders (requires authentication)"""
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
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
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
    db: Session = Depends(get_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
    """Update order status (requires authentication)"""
    try:
        status_enum = OrderStatus(new_status)
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
    db: Session = Depends(get_db),
    order_service: OrderService = Depends(get_order_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get orders by client ID (requires authentication)"""
    orders = order_service.get_orders_by_client(db, client_id, skip=skip, limit=limit)
    return orders 