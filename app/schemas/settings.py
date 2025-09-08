from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class SettingsBase(BaseModel):
    company_name: str
    business_name: str
    nit: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    is_active: bool = True


class SettingsCreate(SettingsBase):
    pass


class SettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    business_name: Optional[str] = None
    nit: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    is_active: Optional[bool] = None


class SettingsResponse(SettingsBase):
    id: int
    logo_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LogoUploadResponse(BaseModel):
    logo_url: str
    message: str


class SettingsFormData(BaseModel):
    """Schema para recibir datos del formulario de settings"""
    company_name: str
    business_name: str
    nit: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
