from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None
    tenant_id: Optional[int] = None
    tenant_schema: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str
    subdominio: Optional[str] = None
