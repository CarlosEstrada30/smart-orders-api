from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ...schemas.user import UserCreate, UserUpdate, UserResponse
from ...services.user_service import UserService
from ..dependencies import get_user_service
from .auth import get_current_active_user, get_tenant_db
from ...models.user import User, UserRole
from ...utils.permissions import can_manage_users

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse,
             status_code=status.HTTP_201_CREATED)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_tenant_db),
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new user (requires admin role)"""
    # Verificar permisos de administrador
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para crear usuarios. Se requiere rol de Administrador."
        )

    try:
        return user_service.create_user(db, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[UserResponse])
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_tenant_db),
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get all users (requires admin role)"""
    # Verificar permisos de administrador
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver usuarios. Se requiere rol de Administrador."
        )

    return user_service.get_users(db, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_tenant_db),
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get a specific user by ID (admin or own profile)"""
    # Los usuarios pueden ver su propio perfil, los admins pueden ver
    # cualquiera
    if user_id != current_user.id and not can_manage_users(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver este usuario."
        )

    user = user_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_tenant_db),
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user)
):
    """Update a user (admin can edit all, users can edit their own basic info)"""
    is_admin = can_manage_users(current_user)
    is_own_profile = user_id == current_user.id

    # Solo admins o el propio usuario pueden actualizar
    if not is_admin and not is_own_profile:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para editar este usuario."
        )

    # Si no es admin y está editando su propio perfil, restringir ciertos
    # campos
    if not is_admin and is_own_profile:
        # Los usuarios no pueden cambiar su rol, estado activo o permisos de
        # superuser
        restricted_fields = ['role', 'is_active', 'is_superuser']
        for field in restricted_fields:
            if hasattr(
                    user_update,
                    field) and getattr(
                    user_update,
                    field) is not None:
                raise HTTPException(
                    status_code=403,
                    detail=(f"No tienes permisos para cambiar '{field}'. "
                            "Solo los administradores pueden modificar roles y permisos.")
                )

    user = user_service.update_user(db, user_id, user_update)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_tenant_db),
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a user (requires admin role)"""
    # Solo administradores pueden eliminar usuarios
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para eliminar usuarios. Se requiere rol de Administrador."
        )

    # Prevenir auto-eliminación
    if user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="No puedes eliminar tu propia cuenta."
        )

    user = user_service.delete_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return None


@router.post("/{user_id}/assign-role", response_model=UserResponse)
def assign_user_role(
    user_id: int,
    new_role: UserRole,
    db: Session = Depends(get_tenant_db),
    user_service: UserService = Depends(get_user_service),
    current_user: User = Depends(get_current_active_user)
):
    """Assign a role to a user (requires admin role)"""
    # Solo administradores pueden asignar roles
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para asignar roles. Se requiere rol de Administrador."
        )

    # Obtener el usuario a actualizar
    target_user = user_service.get_user(db, user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Crear objeto de actualización solo con el rol
    user_update = UserUpdate(role=new_role)

    # Actualizar el usuario
    updated_user = user_service.update_user(db, user_id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    return updated_user


@router.get("/roles/available", response_model=dict)
def get_available_roles(
    current_user: User = Depends(get_current_active_user)
):
    """Get list of available user roles (requires admin role)"""
    # Solo administradores pueden ver la lista de roles disponibles
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver roles disponibles. Se requiere rol de Administrador."
        )

    return {
        "available_roles": [
            {
                "value": role.value,
                "name": role.value.replace("_", " ").title(),
                "description": get_role_description(role)
            }
            for role in UserRole
        ]
    }


def get_role_description(role: UserRole) -> str:
    """Get description for each role"""
    descriptions = {
        UserRole.EMPLOYEE: "Empleado básico (almacén/producción)",
        UserRole.SALES: "Vendedor (pedidos y clientes)",
        UserRole.DRIVER: "Repartidor (entregas)",
        UserRole.SUPERVISOR: "Supervisor (aprobaciones)",
        UserRole.MANAGER: "Gerente (reportes y gestión)",
        UserRole.ADMIN: "Administrador (gestión completa del sistema)"
    }
    return descriptions.get(role, "Rol sin descripción")
