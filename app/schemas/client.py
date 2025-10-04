from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime


class ClientBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    nit: Optional[str] = None
    address: Optional[str] = None
    is_active: bool = True

    @field_validator('email', mode='before')
    @classmethod
    def validate_email(cls, v):
        if v == "" or v is None:
            return None
        return v


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    nit: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator('email', mode='before')
    @classmethod
    def validate_email(cls, v):
        if v == "" or v is None:
            return None
        return v


class ClientResponse(ClientBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
