from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from ...database import get_db
from ...schemas.auth import Token, LoginRequest
from ...services.auth_service import AuthService
from ...services.user_service import UserService
from ...models.user import User
from ...utils.permissions import get_user_permissions

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


def get_auth_service() -> AuthService:
    return AuthService()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    user = auth_service.get_current_user(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@router.post("/login", response_model=Token)
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Login endpoint to authenticate user and get JWT token"""
    user = auth_service.authenticate_user(db, login_data.email, login_data.password)
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
    
    access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
    access_token = auth_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=dict)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
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
def get_current_user_permissions(current_user: User = Depends(get_current_active_user)):
    """Get current user permissions for frontend"""
    return get_user_permissions(current_user) 