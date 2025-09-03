from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class TenantBase(BaseModel):
    nombre: str
    subdominio: str


class TenantCreate(TenantBase):
    is_trial: Optional[bool] = False  # Por defecto no es de prueba


class TenantUpdate(BaseModel):
    nombre: Optional[str] = None
    subdominio: Optional[str] = None
    is_trial: Optional[bool] = None
    # token no es actualizable, se autogenera como UUID
    # active se maneja internamente para soft delete


class TenantResponse(TenantBase):
    id: int
    token: str
    schema_name: str
    active: bool
    is_trial: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
