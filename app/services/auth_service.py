from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from ..config import settings
from ..services.user_service import UserService
from ..schemas.auth import TokenData


class AuthService:
    def __init__(self):
        self.user_service = UserService()
        self.secret_key = settings.SECRET_KEY
        self.algorithm = settings.ALGORITHM
        self.access_token_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES

    def create_access_token(
            self,
            data: dict,
            expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            self.secret_key,
            algorithm=self.algorithm)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(
                token, self.secret_key, algorithms=[
                    self.algorithm])
            email: str = payload.get("sub")
            if email is None:
                return None

            # Extraer información del usuario del token (estructura anidada)
            user_info = payload.get("user", {})

            # Extraer información del tenant del token (estructura anidada)
            tenant_info = payload.get("tenant", {})
            tenant_id = tenant_info.get("tenant_id")
            tenant_schema = tenant_info.get("tenant_schema")

            token_data = TokenData(
                email=email,
                user=user_info,
                tenant_id=tenant_id,
                tenant_schema=tenant_schema
            )
            return token_data
        except JWTError:
            return None

    def authenticate_user(self, db: Session, email: str, password: str):
        """Authenticate user with email and password"""
        return self.user_service.authenticate_user(db, email, password)

    def get_current_user(self, db: Session, token: str):
        """Get current user from JWT token"""
        token_data = self.verify_token(token)
        if token_data is None:
            return None
        user = self.user_service.get_user_by_email(db, email=token_data.email)
        return user
