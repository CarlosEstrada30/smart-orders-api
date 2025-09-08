from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ...database import get_db
from ...schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from ...services.tenant_service import TenantService
from ..dependencies import get_tenant_service
from .auth import get_current_active_user
from ...models.user import User
from ...utils.permissions import can_manage_users

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("/", response_model=TenantResponse,
             status_code=status.HTTP_201_CREATED)
def create_tenant(
    tenant: TenantCreate,
    db: Session = Depends(get_db),
    tenant_service: TenantService = Depends(get_tenant_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Crear un nuevo tenant con su schema y migraciones

    Este endpoint:
    1. Crea el registro del tenant en el schema public
    2. Crea un nuevo schema de base de datos con el nombre generado
    3. Ejecuta las migraciones en el nuevo schema
    4. Crea un superusuario por defecto: admin@{subdominio}.com con password admin{subdominio}123

    Requiere permisos de administrador.
    """
    # Solo administradores pueden crear tenants
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para crear tenants. Se requiere rol de Administrador."
        )

    try:
        db_tenant = tenant_service.create_tenant(db, tenant)
        # El campo schema se incluye automáticamente en la respuesta
        return TenantResponse.model_validate(db_tenant)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al crear tenant: {str(e)}"
        )


@router.get("/", response_model=List[TenantResponse])
def get_tenants(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    tenant_service: TenantService = Depends(get_tenant_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener lista de todos los tenants

    Requiere permisos de administrador.
    """
    # Solo administradores pueden ver la lista de tenants
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver tenants. Se requiere rol de Administrador."
        )

    tenants = tenant_service.get_tenants(db, skip=skip, limit=limit)
    return [TenantResponse.model_validate(tenant) for tenant in tenants]


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    tenant_service: TenantService = Depends(get_tenant_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener un tenant específico por ID

    Requiere permisos de administrador.
    """
    # Solo administradores pueden ver tenants específicos
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver este tenant. Se requiere rol de Administrador."
        )

    tenant = tenant_service.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    return TenantResponse.model_validate(tenant)


@router.get("/by-token/{token}", response_model=TenantResponse)
def get_tenant_by_token(
    token: str,
    db: Session = Depends(get_db),
    tenant_service: TenantService = Depends(get_tenant_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener un tenant por su token

    Requiere permisos de administrador.
    """
    # Solo administradores pueden buscar tenants por token
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para buscar tenants. Se requiere rol de Administrador."
        )

    tenant = tenant_service.get_tenant_by_token(db, token)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    return TenantResponse.model_validate(tenant)


@router.get("/by-subdomain/{subdominio}", response_model=TenantResponse)
def get_tenant_by_subdominio(
    subdominio: str,
    db: Session = Depends(get_db),
    tenant_service: TenantService = Depends(get_tenant_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener un tenant por su subdominio

    Requiere permisos de administrador.
    """
    # Solo administradores pueden buscar tenants por subdominio
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para buscar tenants. Se requiere rol de Administrador."
        )

    tenant = tenant_service.get_tenant_by_subdominio(db, subdominio)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    return TenantResponse.model_validate(tenant)


@router.put("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: int,
    tenant_update: TenantUpdate,
    db: Session = Depends(get_db),
    tenant_service: TenantService = Depends(get_tenant_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Actualizar un tenant

    Requiere permisos de administrador.
    NOTA: Cambiar el token o nombre no actualizará automáticamente el nombre del schema.
    """
    # Solo administradores pueden actualizar tenants
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para actualizar tenants. Se requiere rol de Administrador."
        )

    try:
        tenant = tenant_service.update_tenant(db, tenant_id, tenant_update)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant no encontrado")

        return TenantResponse.model_validate(tenant)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    tenant_service: TenantService = Depends(get_tenant_service),
    current_user: User = Depends(get_current_active_user)
):
    """
    Eliminar un tenant

    ADVERTENCIA: Esta operación es irreversible y eliminará el registro del tenant.
    El schema de base de datos asociado NO se eliminará automáticamente por seguridad.

    Requiere permisos de administrador.
    """
    # Solo administradores pueden eliminar tenants
    if not can_manage_users(current_user):
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para eliminar tenants. Se requiere rol de Administrador."
        )

    tenant = tenant_service.delete_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    return None
