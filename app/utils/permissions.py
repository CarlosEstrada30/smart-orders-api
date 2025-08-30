from typing import List
from ..models.user import User, UserRole


def has_permission(user: User, required_roles: List[UserRole]) -> bool:
    """
    Verifica si el usuario tiene al menos uno de los roles requeridos
    """
    if not user.is_active:
        return False
    
    # Superuser siempre tiene acceso
    if user.is_superuser:
        return True
    
    # Manejar el caso cuando user.role es None (usuarios existentes antes de la migración)
    current_role = user.role if user.role else UserRole.EMPLOYEE
    
    # Verificar si el rol del usuario está en los roles requeridos
    return current_role in required_roles


def can_manage_inventory(user: User) -> bool:
    """Puede gestionar inventario (crear, ver)"""
    return has_permission(user, [UserRole.EMPLOYEE, UserRole.SUPERVISOR, UserRole.MANAGER, UserRole.ADMIN])


def can_approve_inventory(user: User) -> bool:
    """Puede aprobar entradas de inventario"""
    return has_permission(user, [UserRole.SUPERVISOR, UserRole.MANAGER, UserRole.ADMIN])


def can_complete_inventory(user: User) -> bool:
    """Puede completar entradas de inventario (actualizar stock)"""
    return has_permission(user, [UserRole.SUPERVISOR, UserRole.MANAGER, UserRole.ADMIN])


def can_manage_orders(user: User) -> bool:
    """Puede crear y gestionar pedidos"""
    return has_permission(user, [UserRole.SALES, UserRole.SUPERVISOR, UserRole.MANAGER, UserRole.ADMIN])


def can_create_orders(user: User) -> bool:
    """Puede crear nuevos pedidos"""
    return has_permission(user, [UserRole.SALES, UserRole.SUPERVISOR, UserRole.MANAGER, UserRole.ADMIN])


def can_view_orders(user: User) -> bool:
    """Puede ver pedidos"""
    return has_permission(user, [UserRole.SALES, UserRole.DRIVER, UserRole.SUPERVISOR, UserRole.MANAGER, UserRole.ADMIN])


def can_update_delivery_status(user: User) -> bool:
    """Puede actualizar estado de entrega (para repartidores)"""
    return has_permission(user, [UserRole.DRIVER, UserRole.SUPERVISOR, UserRole.MANAGER, UserRole.ADMIN])


def can_manage_clients(user: User) -> bool:
    """Puede gestionar clientes"""
    return has_permission(user, [UserRole.SALES, UserRole.SUPERVISOR, UserRole.MANAGER, UserRole.ADMIN])


def can_view_clients(user: User) -> bool:
    """Puede ver información de clientes"""
    return has_permission(user, [UserRole.SALES, UserRole.DRIVER, UserRole.SUPERVISOR, UserRole.MANAGER, UserRole.ADMIN])


def can_manage_routes(user: User) -> bool:
    """Puede crear y editar rutas"""
    return has_permission(user, [UserRole.SUPERVISOR, UserRole.MANAGER, UserRole.ADMIN])


def can_view_routes(user: User) -> bool:
    """Puede ver rutas"""
    return has_permission(user, [UserRole.SALES, UserRole.DRIVER, UserRole.SUPERVISOR, UserRole.MANAGER, UserRole.ADMIN])


def can_manage_products(user: User) -> bool:
    """Puede crear y editar productos"""
    return has_permission(user, [UserRole.SUPERVISOR, UserRole.MANAGER, UserRole.ADMIN])


def can_view_products(user: User) -> bool:
    """Puede ver catálogo de productos"""
    return has_permission(user, [UserRole.SALES, UserRole.DRIVER, UserRole.SUPERVISOR, UserRole.MANAGER, UserRole.ADMIN])


def can_view_product_prices(user: User) -> bool:
    """Puede ver precios de productos"""
    return has_permission(user, [UserRole.SALES, UserRole.SUPERVISOR, UserRole.MANAGER, UserRole.ADMIN])


def can_view_costs(user: User) -> bool:
    """Puede ver costos de productos e inventario"""
    return has_permission(user, [UserRole.MANAGER, UserRole.ADMIN])


def can_manage_users(user: User) -> bool:
    """Puede gestionar usuarios"""
    return has_permission(user, [UserRole.ADMIN])


def can_view_reports(user: User) -> bool:
    """Puede ver reportes financieros"""
    return has_permission(user, [UserRole.MANAGER, UserRole.ADMIN])


def get_user_permissions(user: User) -> dict:
    """
    Retorna un diccionario con todos los permisos del usuario
    para enviar al frontend
    """
    # Manejar el caso cuando user.role es None (usuarios existentes antes de la migración)
    user_role = user.role.value if user.role else UserRole.EMPLOYEE.value
    
    return {
        "role": user_role,
        "is_superuser": user.is_superuser,
        "permissions": {
            "inventory": {
                "can_manage": can_manage_inventory(user),
                "can_approve": can_approve_inventory(user),
                "can_complete": can_complete_inventory(user)
            },
            "orders": {
                "can_manage": can_manage_orders(user),
                "can_create": can_create_orders(user),
                "can_view": can_view_orders(user),
                "can_update_delivery": can_update_delivery_status(user)
            },
            "products": {
                "can_manage": can_manage_products(user),
                "can_view": can_view_products(user),
                "can_view_prices": can_view_product_prices(user),
                "can_view_costs": can_view_costs(user)
            },
            "clients": {
                "can_manage": can_manage_clients(user),
                "can_view": can_view_clients(user)
            },
            "routes": {
                "can_manage": can_manage_routes(user),
                "can_view": can_view_routes(user)
            },
            "users": {
                "can_manage": can_manage_users(user)
            },
            "reports": {
                "can_view": can_view_reports(user)
            }
        }
    }
