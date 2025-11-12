from typing import List, Optional, Union
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from ...schemas.payment import (
    PaymentCreate, PaymentResponse, OrderPaymentSummary, BulkPaymentCreate, BulkPaymentResponse
)
from ...schemas.pagination import PaginatedResponse
from ...services.payment_service import PaymentService
from ...models.payment import PaymentStatus
from ..dependencies import get_payment_service
from .auth import get_current_active_user, get_tenant_db
from ...models.user import User
from ...utils.date_filters import create_date_range_utc, validate_date_range
from ...middleware import get_request_timezone
from ...utils.permissions import (
    can_manage_payments, can_view_payments, can_cancel_payments
)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=PaymentResponse,
             status_code=status.HTTP_201_CREATED)
def create_payment(
    payment: PaymentCreate,
    db: Session = Depends(get_tenant_db),
    payment_service: PaymentService = Depends(get_payment_service),
    current_user: User = Depends(get_current_active_user)
):
    """Crear un nuevo pago (requiere rol de Vendedor o superior)"""
    # Verificar permisos
    if not can_manage_payments(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para crear pagos. Se requiere rol de Vendedor o superior."
        )

    try:
        return payment_service.create_payment(
            db,
            payment_data=payment,
            created_by_user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[PaymentResponse])
def get_payments(
    skip: int = 0,
    limit: int = 100,
    order_id: Optional[int] = Query(None, description="Filtrar por ID de orden"),
    payment_method: Optional[str] = Query(None, description="Filtrar por método de pago"),
    status_filter: Optional[str] = Query(None, description="Filtrar por estado"),
    date_from: Optional[date] = Query(None, description="Filtrar desde esta fecha (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Filtrar hasta esta fecha (YYYY-MM-DD)"),
    only_confirmed: bool = Query(True, description="Solo mostrar pagos confirmados"),
    db: Session = Depends(get_tenant_db),
    payment_service: PaymentService = Depends(get_payment_service),
    current_user: User = Depends(get_current_active_user),
    request: Request = None
):
    """Obtener lista de pagos con filtros opcionales (requiere permiso de ver pagos)"""
    # Verificar permisos
    if not can_view_payments(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver pagos."
        )

    # Validar rango de fechas
    validate_date_range(date_from, date_to)

    # Convertir status filter a enum si se proporciona
    status_enum = None
    if status_filter:
        try:
            status_enum = PaymentStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Estado inválido: {status_filter}. Valores válidos: confirmed, cancelled"
            )

    # Obtener timezone del cliente y convertir fechas a UTC
    client_timezone = get_request_timezone(request) if request else None
    if client_timezone:
        date_from_utc, date_to_utc = create_date_range_utc(date_from, date_to, client_timezone)
    else:
        date_from_utc = date_from
        date_to_utc = date_to

    # Obtener pagos con filtros
    if any([order_id, payment_method, status_enum, date_from_utc, date_to_utc]):
        return payment_service.get_payments_with_filters(
            db,
            skip=skip,
            limit=limit,
            order_id=order_id,
            payment_method=payment_method,
            status=status_enum,
            date_from=date_from_utc,
            date_to=date_to_utc,
            only_confirmed=only_confirmed
        )
    else:
        return payment_service.get_payments(
            db,
            skip=skip,
            limit=limit,
            only_confirmed=only_confirmed
        )


@router.get("/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_tenant_db),
    payment_service: PaymentService = Depends(get_payment_service),
    current_user: User = Depends(get_current_active_user)
):
    """Obtener un pago específico por ID (requiere autenticación)"""
    payment = payment_service.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    return payment


@router.post("/bulk", response_model=BulkPaymentResponse,
             status_code=status.HTTP_201_CREATED)
def create_bulk_payments(
    bulk_payment: BulkPaymentCreate,
    db: Session = Depends(get_tenant_db),
    payment_service: PaymentService = Depends(get_payment_service),
    current_user: User = Depends(get_current_active_user)
):
    """Crear múltiples pagos en un solo request (requiere rol de Vendedor o superior)
    
    Permite pagar múltiples órdenes en una sola transacción. Si algunos pagos fallan,
    los pagos válidos se procesarán y se reportarán los que fallaron.
    """
    # Verificar permisos
    if not can_manage_payments(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para crear pagos. Se requiere rol de Vendedor o superior."
        )

    try:
        return payment_service.create_bulk_payments(
            db,
            payments_data=bulk_payment.payments,
            created_by_user_id=current_user.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al procesar pagos: {str(e)}")


@router.post("/{payment_id}/cancel", response_model=PaymentResponse)
def cancel_payment(
    payment_id: int,
    db: Session = Depends(get_tenant_db),
    payment_service: PaymentService = Depends(get_payment_service),
    current_user: User = Depends(get_current_active_user)
):
    """Cancelar un pago (requiere rol de Vendedor o superior)"""
    # Verificar permisos
    if not can_cancel_payments(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para cancelar pagos. Se requiere rol de Vendedor o superior."
        )

    try:
        payment = payment_service.cancel_payment(db, payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Pago no encontrado")
        return payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

