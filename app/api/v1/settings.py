from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ...schemas.settings import SettingsResponse, SettingsFormData
from ...services.settings_service import SettingsService
from ...services.auth_service import AuthService
from ...services.tenant_service import TenantService
from ..dependencies import get_settings_service, get_auth_service, get_tenant_service
from .auth import get_current_active_user, get_tenant_db
from ...models.user import User
from ...models.tenant import Tenant
from ...database import get_db

router = APIRouter(prefix="/settings", tags=["settings"])

security = HTTPBearer()

# Tipos de archivo permitidos para logos
ALLOWED_LOGO_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/gif": [".gif"],
    "image/webp": [".webp"]
}

MAX_LOGO_SIZE = 5 * 1024 * 1024  # 5MB


def get_current_tenant(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    tenant_service: TenantService = Depends(get_tenant_service),
    db: Session = Depends(get_db)
) -> Optional[Tenant]:
    """
    Obtiene el tenant actual desde el JWT token.
    Si el tenant_schema es "public", crea un objeto Tenant en memoria.
    Retorna None solo si no se puede decodificar el token.
    """
    try:
        # Decodificar el token para obtener información del tenant
        token_data = auth_service.verify_token(credentials.credentials)
        if not token_data:
            return None

        # Si el tenant_schema es "public", crear un objeto Tenant en memoria
        if token_data.tenant_schema == "public":
            tenant = Tenant(
                id=0,  # ID ficticio para tenant público
                token="public",
                nombre="Public",
                subdominio="public",
                schema_name="public",
                active=True,
                is_trial=False
            )
            return tenant

        # Si hay tenant_id, obtener el tenant completo desde la base de datos public
        if token_data.tenant_id:
            tenant = tenant_service.get_tenant(db, token_data.tenant_id)
            return tenant

        # Si hay tenant_schema pero no tenant_id, crear tenant en memoria con el schema
        if token_data.tenant_schema:
            tenant = Tenant(
                id=0,  # ID ficticio
                token=token_data.tenant_schema,
                nombre=token_data.tenant_schema.title(),
                subdominio=token_data.tenant_schema,
                schema_name=token_data.tenant_schema,
                active=True,
                is_trial=False
            )
            return tenant

        return None

    except Exception:
        return None


def _validate_logo_file(logo: UploadFile, content: bytes) -> None:
    """Valida el archivo de logo"""
    # Validar tipo de archivo
    if logo.content_type not in ALLOWED_LOGO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type {logo.content_type} not allowed. Allowed types: {', '.join(ALLOWED_LOGO_TYPES.keys())}"
        )

    # Validar tamaño de archivo
    if len(content) > MAX_LOGO_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed size of {MAX_LOGO_SIZE / 1024 / 1024:.1f}MB"
        )

    # Validar extensión de archivo
    filename = logo.filename or ""
    file_extension = filename.lower().split('.')[-1] if '.' in filename else ""
    if f".{file_extension}" not in ALLOWED_LOGO_TYPES.get(
            logo.content_type, []):
        raise HTTPException(
            status_code=400,
            detail="File extension doesn't match content type"
        )


@router.get("/", response_model=Optional[SettingsResponse])
def get_company_settings(
    db: Session = Depends(get_tenant_db),
    settings_service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(get_current_active_user)
):
    """Get company settings (requires authentication)"""
    return settings_service.get_company_settings(db)


def _create_settings_from_form(
    company_name: str,
    business_name: str,
    nit: str,
    address: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    website: Optional[str] = None
) -> SettingsFormData:
    """Crea un objeto SettingsFormData desde los campos del formulario"""
    return SettingsFormData(
        company_name=company_name,
        business_name=business_name,
        nit=nit,
        address=address,
        phone=phone,
        email=email,
        website=website
    )


@router.post("/", response_model=SettingsResponse,
             status_code=status.HTTP_200_OK)
async def save_company_settings(
    company_name: str = Form(...),
    business_name: str = Form(...),
    nit: str = Form(...),
    address: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    website: Optional[str] = Form(None),
    logo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_tenant_db),
    settings_service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(get_current_active_user),
    current_tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """
    Create or update company settings with optional logo upload in a single request

    This endpoint handles both creating new settings and updating existing ones.
    Only one settings record is allowed per tenant.
    """
    try:
        # Crear objeto schema desde form data
        settings_form = _create_settings_from_form(
            company_name=company_name,
            business_name=business_name,
            nit=nit,
            address=address,
            phone=phone,
            email=email,
            website=website
        )

        # Convertir a dict para el service (manteniendo solo campos no None)
        settings_data = settings_form.model_dump(exclude_unset=True)
        settings_data["is_active"] = True

        # Procesar logo si se proporciona
        logo_file = None
        logo_filename = None
        logo_content_type = None

        if logo:
            content = await logo.read()
            _validate_logo_file(logo, content)

            from io import BytesIO
            logo_file = BytesIO(content)
            logo_filename = logo.filename
            logo_content_type = logo.content_type

        # Crear o actualizar settings
        result = settings_service.create_or_update_settings(
            db=db,
            settings_data=settings_data,
            logo_file=logo_file,
            logo_filename=logo_filename,
            logo_content_type=logo_content_type,
            tenant_token=current_tenant.token if current_tenant else None
        )

        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/logo", status_code=status.HTTP_204_NO_CONTENT)
def delete_company_logo(
    db: Session = Depends(get_tenant_db),
    settings_service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(get_current_active_user),
    current_tenant: Optional[Tenant] = Depends(get_current_tenant)
):
    """Delete company logo from R2 and database (requires authentication)"""
    try:
        # Obtener settings activo
        current_settings = settings_service.get_company_settings(db)
        if not current_settings:
            raise HTTPException(status_code=404, detail="Settings not found")

        success = settings_service.delete_logo(
            db,
            current_settings.id,
            tenant_token=current_tenant.token if current_tenant else None
        )
        if not success:
            raise HTTPException(status_code=404, detail="Logo not found")
        return None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
def delete_company_settings(
    db: Session = Depends(get_tenant_db),
    settings_service: SettingsService = Depends(get_settings_service),
    current_user: User = Depends(get_current_active_user)
):
    """Delete company settings (soft delete) (requires authentication)"""
    current_settings = settings_service.get_company_settings(db)
    if not current_settings:
        raise HTTPException(status_code=404, detail="Settings not found")

    settings = settings_service.deactivate_settings(db, current_settings.id)
    if not settings:
        raise HTTPException(status_code=404, detail="Settings not found")
    return None
