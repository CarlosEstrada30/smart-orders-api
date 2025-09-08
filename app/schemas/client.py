from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class ClientBase(BaseModel):
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    nit: Optional[str] = None
    address: Optional[str] = None
    is_active: bool = True


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    nit: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class ClientResponse(ClientBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
