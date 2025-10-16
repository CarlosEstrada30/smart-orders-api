"""
Configuración simple para pytest con PostgreSQL.

Este archivo contiene fixtures básicos para tests que usan PostgreSQL.
La conexión se toma de la variable de entorno DATABASE_URL.
"""

import os
import pytest
from jose import jwt
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from app.main import app
from app.database import get_db, Base
from app.models.user import User, UserRole
from passlib.context import CryptContext

# Importar factories
from tests import factories

# Obtener URL de base de datos desde variable de entorno
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost:5432/test_db')

# Crear motor de base de datos
engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool,  # No usar pool para tests
    echo=False,  # Cambiar a True para ver las queries SQL
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine)

# Contexto para hashear contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_test_jwt(secret_key: str = None, exp: int = None) -> str:
    """
    Crear un JWT para tests con la estructura específica requerida.

    Args:
        secret_key: Clave secreta para firmar el JWT (por defecto usa SECRET_KEY del entorno)
        exp: Timestamp de expiración (por defecto 1 año en el futuro)

    Returns:
        JWT firmado como string
    """
    if secret_key is None:
        secret_key = os.getenv(
            'SECRET_KEY',
            'test-secret-key-for-testing-only')

    if exp is None:
        # 1 año en el futuro
        exp = int((datetime.now() + timedelta(days=365)).timestamp())

    # Payload con la estructura específica requerida
    payload = {
        "sub": "admin@example.com",
        "user": {
            "id": 1,
            "email": "admin@example.com",
            "username": "admin",
            "full_name": "Administrador",
            "token": "b0d238cb-7f18-48c1-8c19-0908e7332df2",
            "role": "EMPLOYEE",
            "is_active": True,
            "is_superuser": True
        },
        "tenant": {
            "tenant_schema": "public"
        },
        "exp": exp
    }

    # Crear y firmar el JWT
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token


@pytest.fixture(scope="function")
def test_user(db_session: Session):
    """
    Fixture que crea un usuario de prueba que coincide con el JWT.
    """
    # Verificar si el usuario ya existe
    existing_user = db_session.query(User).filter_by(id=1).first()
    if existing_user:
        return existing_user

    # Crear usuario que coincide con el JWT
    test_user = User(
        id=1,
        email="admin@example.com",
        username="admin",
        full_name="Administrador",
        hashed_password=pwd_context.hash("test-password"),
        token="b0d238cb-7f18-48c1-8c19-0908e7332df2",
        is_active=True,
        is_superuser=True,
        role=UserRole.EMPLOYEE
    )

    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    return test_user


@pytest.fixture(scope="function")
def db_session() -> Session:
    """
    Fixture que proporciona una sesión de base de datos PostgreSQL para cada test.
    - Crea todas las tablas al inicio
    - Limpia todas las tablas al final
    """
    # Crear todas las tablas
    Base.metadata.create_all(bind=engine)

    # Crear sesión
    session = TestingSessionLocal()

    yield session

    # Limpiar después del test
    session.close()

    # Eliminar todas las tablas
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session: Session):
    """
    Fixture que proporciona un cliente de pruebas FastAPI con PostgreSQL.
    Incluye un JWT fijo para evitar hacer login en cada test.
    """
    def override_get_db():
        return db_session

    # Reemplazar la dependencia get_db con nuestra sesión de test
    app.dependency_overrides[get_db] = override_get_db

    try:
        test_client = TestClient(app)
        yield test_client
    finally:
        # Restaurar dependencias originales
        app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def authenticated_client(client, test_user):
    """
    Fixture que proporciona un cliente con JWT fijo para autenticación.
    No es necesario hacer login en cada test.
    """
    # Crear JWT con la estructura específica requerida
    test_jwt = create_test_jwt()

    # Headers con JWT fijo
    headers = {"Authorization": f"Bearer {test_jwt}"}

    # Crear cliente con headers por defecto
    class AuthenticatedTestClient:
        def __init__(self, client, headers):
            self.client = client
            self.headers = headers

        def get(self, url, **kwargs):
            if 'headers' not in kwargs:
                kwargs['headers'] = self.headers
            return self.client.get(url, **kwargs)

        def post(self, url, **kwargs):
            if 'headers' not in kwargs:
                kwargs['headers'] = self.headers
            return self.client.post(url, **kwargs)

        def put(self, url, **kwargs):
            if 'headers' not in kwargs:
                kwargs['headers'] = self.headers
            return self.client.put(url, **kwargs)

        def delete(self, url, **kwargs):
            if 'headers' not in kwargs:
                kwargs['headers'] = self.headers
            return self.client.delete(url, **kwargs)

    return AuthenticatedTestClient(client, headers)


@pytest.fixture
def sample_client_data():
    """Datos de cliente de muestra."""
    return {
        "name": "Test Client",
        "email": "client@test.com",
        "phone": "123456789",
        "address": "Test Address 123",
        "nit": "12345678-9"
    }


@pytest.fixture
def sample_product_data():
    """Datos de producto de muestra."""
    return {
        "name": "Test Product",
        "description": "A test product description",
        "price": 99.99,
        "stock": 50,
        "sku": "TEST-PROD-001",
        "is_active": True
    }


# Fixture para configurar todos los factories con la sesión de BD
@pytest.fixture
def setup_factories(db_session):
    """
    Configura todos los factories para usar la sesión de BD actual.

    Uso:
        def test_something(self, setup_factories, db_session):
            from tests.factories import ClientFactory
            client = ClientFactory.create(name="Test Client")
    """
    factories.configure_factories(db_session)
    return factories
