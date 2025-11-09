"""
API dependencies for the application.
"""
from fastapi import Depends, Request
from sqlalchemy.orm import Session
from typing import Tuple
from .v1.auth import get_tenant_db
from ..middleware import get_request_timezone
from ..services.user_service import UserService
from ..services.client_service import ClientService
from ..services.product_service import ProductService
from ..services.order_service import OrderService
from ..services.route_service import RouteService
from ..services.invoice_service import InvoiceService
from ..services.inventory_entry_service import InventoryEntryService
from ..services.settings_service import SettingsService
from ..services.tenant_service import TenantService
from ..services.auth_service import AuthService
from ..services.payment_service import PaymentService


def get_payment_service() -> PaymentService:
    """Get PaymentService instance"""
    return PaymentService()


def get_client_timezone(request: Request) -> str:
    """
    Dependency to get client timezone from request.

    Args:
        request: FastAPI request object

    Returns:
        str: Client timezone string
    """
    return get_request_timezone(request)


def get_timezone_aware_db(
    db: Session = Depends(get_tenant_db),
    client_timezone: str = Depends(get_client_timezone)
) -> Tuple[Session, str]:
    """
    Dependency that provides both database session and client timezone.

    Args:
        db: Database session
        client_timezone: Client timezone string

    Returns:
        tuple: (database_session, client_timezone)
    """
    return db, client_timezone


# Service dependencies
def get_user_service() -> UserService:
    """Get UserService instance"""
    return UserService()


def get_client_service() -> ClientService:
    """Get ClientService instance"""
    return ClientService()


def get_product_service() -> ProductService:
    """Get ProductService instance"""
    return ProductService()


def get_order_service() -> OrderService:
    """Get OrderService instance"""
    return OrderService()


def get_route_service() -> RouteService:
    """Get RouteService instance"""
    return RouteService()


def get_invoice_service() -> InvoiceService:
    """Get InvoiceService instance"""
    return InvoiceService()


def get_inventory_entry_service() -> InventoryEntryService:
    """Get InventoryEntryService instance"""
    return InventoryEntryService()


def get_settings_service() -> SettingsService:
    """Get SettingsService instance"""
    return SettingsService()


def get_tenant_service() -> TenantService:
    """Get TenantService instance"""
    return TenantService()


def get_auth_service() -> AuthService:
    """Get AuthService instance"""
    return AuthService()
