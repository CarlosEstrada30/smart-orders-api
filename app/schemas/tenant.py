from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class TenantBase(BaseModel):
    nombre: str
    subdominio: str


class TenantCreate(TenantBase):
    pass  # Solo necesita nombre y subdominio, el token se autogenera


class TenantUpdate(BaseModel):
    nombre: Optional[str] = None
    subdominio: Optional[str] = None
    # token no es actualizable, se autogenera como UUID


class TenantResponse(TenantBase):
    id: int
    token: str
    schema_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
