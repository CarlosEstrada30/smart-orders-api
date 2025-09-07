"""
Tests de integración para el sistema de autenticación.

Estos tests prueban los endpoints de autenticación de la API.
"""

import pytest
from fastapi.testclient import TestClient
from app.models.user import User
from app.services.user_service import UserService
from app.schemas.user import UserCreate


class TestAuthentication:
    """Tests para el sistema de autenticación."""
    
    def test_successful_login(self, client, db_session, sample_user_data):
        """Test de login exitoso."""
        # Crear un usuario primero
        user_service = UserService()
        user_data = UserCreate(**sample_user_data)
        user_service.create_user(db_session, user_data)
        
        # Intentar login
        login_data = {
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert "token_type" in token_data
        assert token_data["token_type"] == "bearer"
    
    def test_login_with_invalid_email(self, client):
        """Test de login con email inválido."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "anypassword"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
    
    def test_login_with_invalid_password(self, client, db_session, sample_user_data):
        """Test de login con contraseña inválida."""
        # Crear un usuario primero
        user_service = UserService()
        user_data = UserCreate(**sample_user_data)
        user_service.create_user(db_session, user_data)
        
        login_data = {
            "email": sample_user_data["email"],
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
    
    def test_me_endpoint_with_valid_token(self, client, db_session, sample_user_data):
        """Test del endpoint /me con token válido."""
        # Crear usuario y obtener token
        user_service = UserService()
        user_data = UserCreate(**sample_user_data)
        user_service.create_user(db_session, user_data)
        
        # Login para obtener token
        login_data = {
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Usar token en endpoint /me
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 200
        user_info = response.json()
        assert user_info["email"] == sample_user_data["email"]
    
    def test_me_endpoint_without_token(self, client):
        """Test del endpoint /me sin token."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == 401
    
    def test_me_endpoint_with_invalid_token(self, client):
        """Test del endpoint /me con token inválido."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401
    
    def test_protected_endpoint_without_token(self, client):
        """Test de endpoint protegido sin token."""
        response = client.get("/api/v1/users")
        
        assert response.status_code == 401
    
    def test_protected_endpoint_with_valid_token(self, client, db_session, sample_user_data):
        """Test de endpoint protegido con token válido."""
        # Crear usuario admin y obtener token
        user_service = UserService()
        user_data = UserCreate(**sample_user_data)
        user_service.create_user(db_session, user_data)
        
        # Login
        login_data = {
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Acceder a endpoint protegido
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/users", headers=headers)
        
        # Puede ser 200 si tiene permisos, o 403 si no tiene permisos
        assert response.status_code in [200, 403]
    
    @pytest.mark.slow
    def test_token_expiration(self, client, db_session, sample_user_data):
        """Test de expiración de token (marcado como lento)."""
        # Este test podría simular la expiración de tokens
        # Por ahora solo verificamos que el token funciona inicialmente
        user_service = UserService()
        user_data = UserCreate(**sample_user_data)
        user_service.create_user(db_session, user_data)
        
        login_data = {
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        }
        login_response = client.post("/api/v1/auth/login", json=login_data)
        
        assert login_response.status_code == 200
        # En un test real, aquí simularíamos el tiempo pasando
        # o usaríamos tokens con expiración muy corta
