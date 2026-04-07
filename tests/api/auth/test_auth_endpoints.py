# -*- coding: utf-8 -*-
"""
Tests for authentication endpoints.

Covers:
- POST /api/v1/auth/login  (public, schema public)
- GET  /api/v1/auth/me
- GET  /api/v1/auth/permissions
"""

import os
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from tests.conftest import create_test_jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
AUTH_URL = "/api/v1/auth"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_jwt_for_user(user: User) -> str:
    """Generate a valid JWT for any test user."""
    secret = os.getenv("SECRET_KEY", "test-secret-key-for-testing-only")
    payload = {
        "sub": user.email,
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "token": user.token,
            "role": user.role.value if user.role else "EMPLOYEE",
            "is_active": user.is_active,
            "is_superuser": user.is_superuser,
        },
        "tenant": {"tenant_schema": "public"},
        "exp": int((datetime.now() + timedelta(days=365)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def _make_user(db_session: Session, **overrides) -> User:
    """Create and persist a test User with default values."""
    defaults = {
        "email": "extra@example.com",
        "username": "extra_user",
        "full_name": "Extra User",
        "hashed_password": pwd_context.hash("password123"),
        "token": "aaaaaaaa-0000-0000-0000-000000000001",
        "is_active": True,
        "is_superuser": False,
        "role": UserRole.EMPLOYEE,
    }
    defaults.update(overrides)
    user = User(**defaults)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Login (POST /api/v1/auth/login)
# ---------------------------------------------------------------------------

class TestLoginPublic:
    """Login without subdomain → authentication in 'public' schema."""

    def test_login_success(self, client, test_user):
        response = client.post(f"{AUTH_URL}/login", json={
            "email": "admin@example.com",
            "password": "test-password",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, test_user):
        response = client.post(f"{AUTH_URL}/login", json={
            "email": "admin@example.com",
            "password": "wrong-password",
        })
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]

    def test_login_nonexistent_email(self, client, db_session):
        response = client.post(f"{AUTH_URL}/login", json={
            "email": "nobody@example.com",
            "password": "any-password",
        })
        assert response.status_code == 401

    def test_login_inactive_user(self, client, db_session):
        _make_user(db_session,
                   email="inactive@example.com",
                   username="inactive",
                   token="aaaaaaaa-0000-0000-0000-000000000002",
                   is_active=False)

        response = client.post(f"{AUTH_URL}/login", json={
            "email": "inactive@example.com",
            "password": "password123",
        })
        assert response.status_code == 400
        assert "Inactive user" in response.json()["detail"]

    def test_login_without_email_returns_422(self, client):
        response = client.post(f"{AUTH_URL}/login", json={"password": "test-password"})
        assert response.status_code == 422

    def test_login_without_password_returns_422(self, client):
        response = client.post(f"{AUTH_URL}/login", json={"email": "admin@example.com"})
        assert response.status_code == 422

    def test_login_token_contains_correct_data(self, client, test_user):
        response = client.post(f"{AUTH_URL}/login", json={
            "email": "admin@example.com",
            "password": "test-password",
        })
        assert response.status_code == 200

        secret = os.getenv("SECRET_KEY", "test-secret-key-for-testing-only")
        payload = jwt.decode(
            response.json()["access_token"], secret, algorithms=["HS256"]
        )
        assert payload["sub"] == "admin@example.com"
        assert payload["tenant"]["tenant_schema"] == "public"
        assert "user" in payload
        assert payload["user"]["email"] == "admin@example.com"

    def test_login_tenant_not_found(self, client, db_session):
        """Login with nonexistent subdomain must return 404."""
        response = client.post(f"{AUTH_URL}/login", json={
            "email": "admin@example.com",
            "password": "test-password",
            "subdominio": "tenant-does-not-exist",
        })
        assert response.status_code == 404
        assert "Tenant not found" in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /api/v1/auth/me
# ---------------------------------------------------------------------------

class TestGetMe:

    def test_me_success(self, authenticated_client, test_user):
        response = authenticated_client.get(f"{AUTH_URL}/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@example.com"
        assert data["username"] == "admin"
        assert data["is_active"] is True
        assert data["is_superuser"] is True
        assert "role" in data

    def test_me_without_token_returns_403(self, client):
        response = client.get(f"{AUTH_URL}/me")
        assert response.status_code == 403

    def test_me_invalid_token_returns_401(self, client, test_user):
        headers = {"Authorization": "Bearer this.is.not.a.valid.jwt"}
        response = client.get(f"{AUTH_URL}/me", headers=headers)
        assert response.status_code == 401

    def test_me_expired_token_returns_401(self, client, test_user):
        expired_jwt = create_test_jwt(
            exp=int((datetime.now() - timedelta(hours=1)).timestamp())
        )
        headers = {"Authorization": f"Bearer {expired_jwt}"}
        response = client.get(f"{AUTH_URL}/me", headers=headers)
        assert response.status_code == 401

    def test_me_returns_active_user_data(self, client, db_session):
        """Verify /me reflects actual user data from the DB."""
        user = _make_user(db_session,
                          email="active@example.com",
                          username="active_user",
                          token="aaaaaaaa-0000-0000-0000-000000000003",
                          role=UserRole.SALES)
        token = _create_jwt_for_user(user)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"{AUTH_URL}/me", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "active@example.com"
        assert data["role"] == UserRole.SALES.value


# ---------------------------------------------------------------------------
# GET /api/v1/auth/permissions
# ---------------------------------------------------------------------------

class TestGetPermissions:

    def test_permissions_success(self, authenticated_client, test_user):
        response = authenticated_client.get(f"{AUTH_URL}/permissions")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    def test_permissions_without_token_returns_403(self, client):
        response = client.get(f"{AUTH_URL}/permissions")
        assert response.status_code == 403

    def test_superuser_has_all_permissions(self, authenticated_client, test_user):
        response = authenticated_client.get(f"{AUTH_URL}/permissions")
        assert response.status_code == 200
        # Response structure: {"role": ..., "is_superuser": ..., "permissions": {...}}
        perms = response.json()["permissions"]
        assert all(v for group in perms.values() for v in group.values()), \
            "Superuser must have all permissions set to True"

    def test_employee_has_restricted_permissions(self, client, db_session):
        """EMPLOYEE cannot manage users or view reports."""
        employee = _make_user(db_session,
                              email="employee@example.com",
                              username="employee_user",
                              token="aaaaaaaa-0000-0000-0000-000000000004",
                              role=UserRole.EMPLOYEE,
                              is_superuser=False)
        token = _create_jwt_for_user(employee)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"{AUTH_URL}/permissions", headers=headers)
        assert response.status_code == 200
        perms = response.json()["permissions"]
        assert perms["users"]["can_manage"] is False
        assert perms["reports"]["can_view"] is False
        assert perms["orders"]["can_create"] is False

    def test_admin_has_full_permissions(self, client, db_session):
        """ADMIN (non-superuser) has all permissions for the highest role."""
        admin = _make_user(db_session,
                           email="admin_role@example.com",
                           username="admin_role",
                           token="aaaaaaaa-0000-0000-0000-000000000005",
                           role=UserRole.ADMIN,
                           is_superuser=False)
        token = _create_jwt_for_user(admin)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get(f"{AUTH_URL}/permissions", headers=headers)
        assert response.status_code == 200
        perms = response.json()["permissions"]
        assert perms["users"]["can_manage"] is True
        assert perms["reports"]["can_view"] is True
        assert perms["orders"]["can_create"] is True
