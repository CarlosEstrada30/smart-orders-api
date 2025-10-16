"""
Test simple para probar la configuración de PostgreSQL.

Este test verifica que la configuración básica funciona correctamente.
"""

from app.services.client_service import ClientService
from app.schemas.client import ClientCreate
from tests.factories import ClientFactory


class TestClientSimple:
    """Tests simples para verificar la configuración."""

    def test_create_client_success(self, db_session, sample_client_data):
        """Test de creación exitosa de cliente."""
        client_service = ClientService()
        client_data = ClientCreate(**sample_client_data)

        result = client_service.create_client(db_session, client_data)

        assert result is not None
        assert result.name == sample_client_data["name"]
        assert result.email == sample_client_data["email"]
        assert result.phone == sample_client_data["phone"]
        assert result.address == sample_client_data["address"]
        assert result.nit == sample_client_data["nit"]
        assert result.is_active is True
        assert result.id is not None

    def test_get_client_by_id(self, db_session, sample_client_data):
        """Test de obtención de cliente por ID."""
        client_service = ClientService()
        client_data = ClientCreate(**sample_client_data)

        created_client = client_service.create_client(db_session, client_data)

        result = client_service.get_client(db_session, created_client.id)

        assert result is not None
        assert result.id == created_client.id
        assert result.name == created_client.name

    def test_create_client_endpoint(
            self,
            authenticated_client,
            db_session,
            sample_client_data):
        """Test del endpoint de crear cliente."""
        response = authenticated_client.post(
            "/api/v1/clients/", json=sample_client_data)

        assert response.status_code == 201
        client_data = response.json()
        assert client_data["name"] == sample_client_data["name"]
        assert client_data["email"] == sample_client_data["email"]
        assert client_data["phone"] == sample_client_data["phone"]
        assert client_data["address"] == sample_client_data["address"]
        assert client_data["nit"] == sample_client_data["nit"]
        assert client_data["is_active"] is True
        assert "id" in client_data
        assert "created_at" in client_data

        # Verificar que el cliente se creó en la BD
        client_service = ClientService()
        db_client = client_service.get_client(db_session, client_data["id"])

        assert db_client is not None
        assert db_client.id == client_data["id"]
        assert db_client.name == sample_client_data["name"]
        assert db_client.email == sample_client_data["email"]
        assert db_client.phone == sample_client_data["phone"]
        assert db_client.address == sample_client_data["address"]
        assert db_client.nit == sample_client_data["nit"]
        assert db_client.is_active is True

    def test_get_clients_endpoint(self, authenticated_client, setup_factories):
        """Test del endpoint de obtener clientes."""
        # Crear un cliente usando el factory (ya configurado con la sesión)
        ClientFactory.create(name="Test Company", email="test@example.com")

        # Obtener lista de clientes
        response = authenticated_client.get("/api/v1/clients/")

        assert response.status_code == 200
        clients = response.json()
        assert len(clients) == 1
        assert clients[0]["name"] == "Test Company"
        assert clients[0]["email"] == "test@example.com"

    def test_create_client_without_authentication(
            self, client, sample_client_data):
        """Test de creación de cliente sin autenticación (debería fallar)."""
        response = client.post("/api/v1/clients/", json=sample_client_data)

        # FastAPI HTTPBearer devuelve 403 cuando no hay header de autenticación
        assert response.status_code == 403

    def test_create_client_with_minimal_data(self, authenticated_client):
        """Test de creación de cliente con datos mínimos."""
        minimal_data = {"name": "Minimal Client"}

        response = authenticated_client.post(
            "/api/v1/clients/", json=minimal_data)

        assert response.status_code == 201
        client_data = response.json()
        assert client_data["name"] == "Minimal Client"
        assert client_data["email"] is None
        assert client_data["phone"] is None
        assert client_data["address"] is None
        assert client_data["nit"] is None
        assert client_data["is_active"] is True
