from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ...database import get_db
from ...schemas.auth import Token, LoginRequest
from ...services.auth_service import AuthService
from ...services.tenant_service import TenantService
from ...models.user import User
from ...utils.permissions import get_user_permissions
from ...utils.tenant_db import get_session_for_schema

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


def get_auth_service() -> AuthService:
    return AuthService()


def get_tenant_service() -> TenantService:
    return TenantService()


def get_tenant_db(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Extrae el tenant_schema del JWT y retorna la sesión de BD correspondiente.

    Funciona tanto para esquema 'public' como para tenants específicos.
    Esta es la función central para multi-tenancy.
    
    IMPORTANTE: Usa yield para que FastAPI cierre automáticamente la sesión.
    """
    db = None
    try:
        # Verificar y decodificar el JWT
        token_data = auth_service.verify_token(credentials.credentials)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extraer el schema del tenant (puede ser "public" o schema específico)
        tenant_schema = token_data.tenant_schema
        if not tenant_schema:
            # Fallback a public si no hay tenant_schema en el JWT
            tenant_schema = "public"

        # Obtener sesión para el schema correspondiente
        if tenant_schema == "public":
            # Para el schema público, usar la sesión principal con reintentos
            from ...database import get_db_with_retries
            db = get_db_with_retries()
        else:
            # Para schemas de tenant específicos
            db = get_session_for_schema(tenant_schema)

        yield db

    except HTTPException:
        # Re-lanzar HTTPExceptions para que FastAPI las maneje correctamente
        if db:
            db.close()
        raise
    except Exception as e:
        # Manejar otros errores
        if db:
            db.close()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    finally:
        # Asegurar que la sesión se cierre
        if db:
            try:
                db.close()
            except Exception as e:
                # Log el error pero no fallar
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Error closing tenant session: {e}")


def get_current_user(
    tenant_db: Session = Depends(get_tenant_db),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """Get current authenticated user from JWT token using tenant-specific database"""
    token = credentials.credentials
    user = auth_service.get_current_user(tenant_db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_active_user(
        current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@router.post("/login", response_model=Token)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """Login endpoint to authenticate user with tenant support and get JWT token"""

    # Si no se especifica subdominio, usar el esquema public por defecto
    if not login_data.subdominio:
        # Autenticación en esquema public (sin tenant específico)
        user = auth_service.authenticate_user(
            db, login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        # Crear JWT sin información de tenant específico (esquema public)
        access_token_expires = timedelta(
            minutes=auth_service.access_token_expire_minutes)
        token_data = {
            "sub": user.email,
            "tenant": {
                "tenant_schema": "public"
            }
        }

        access_token = auth_service.create_access_token(
            data=token_data, expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}

    # Si se especifica subdominio, procesar con lógica de tenant
    else:
        # 1. Buscar el tenant por subdominio en el esquema public
        tenant = tenant_service.get_tenant_by_subdominio(
            db, login_data.subdominio)
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found for the provided subdomain",
            )

        # 2. Crear sesión específica para el schema del tenant
        tenant_db = get_session_for_schema(tenant.schema_name)

        try:
            # 3. Autenticar usuario en el schema del tenant
            user = auth_service.authenticate_user(
                tenant_db, login_data.email, login_data.password)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Inactive user"
                )

            # 4. Crear JWT con información del tenant
            access_token_expires = timedelta(
                minutes=auth_service.access_token_expire_minutes)
            token_data = {
                "sub": user.email,
                "tenant": {
                    "tenant_id": tenant.id,
                    "tenant_schema": tenant.schema_name,
                    "tenant_name": tenant.nombre,
                    "tenant_subdomain": tenant.subdominio
                }
            }

            access_token = auth_service.create_access_token(
                data=token_data, expires_delta=access_token_expires
            )

            return {"access_token": access_token, "token_type": "bearer"}

        finally:
            # 5. Cerrar la sesión del tenant
            tenant_db.close()


@router.get("/me", response_model=dict)
def get_current_user_info(
        current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "role": current_user.role.value if current_user.role else "employee"
    }


@router.get("/permissions", response_model=dict)
def get_current_user_permissions(
        current_user: User = Depends(get_current_active_user)):
    """Get current user permissions for frontend"""
    return get_user_permissions(current_user)
