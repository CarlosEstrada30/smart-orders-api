from sqlalchemy.orm import Session
from ..database import get_db
from ..services.user_service import UserService
from ..services.client_service import ClientService
from ..services.product_service import ProductService
from ..services.order_service import OrderService
from ..services.route_service import RouteService
from ..services.auth_service import AuthService
from ..services.invoice_service import InvoiceService
from ..services.inventory_entry_service import InventoryEntryService
from ..services.tenant_service import TenantService
from ..services.settings_service import SettingsService


def get_user_service() -> UserService:
    return UserService()


def get_client_service() -> ClientService:
    return ClientService()


def get_product_service() -> ProductService:
    return ProductService()


def get_order_service() -> OrderService:
    return OrderService()


def get_route_service() -> RouteService:
    return RouteService()


def get_auth_service() -> AuthService:
    return AuthService()


def get_invoice_service() -> InvoiceService:
    return InvoiceService()


def get_inventory_entry_service() -> InventoryEntryService:
    return InventoryEntryService()


def get_tenant_service() -> TenantService:
    return TenantService()


def get_settings_service() -> SettingsService:
    return SettingsService() 