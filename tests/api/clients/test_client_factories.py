"""
Tests simples que demuestran el uso de ClientFactory.
"""

from tests.factories import ClientFactory


class TestClientFactory:
    """Tests simples para ClientFactory."""

    def test_create_client_with_factory(self, setup_factories):
        """Test de creación de cliente usando factory."""
        # Crear cliente directamente en la BD con factory
        client = ClientFactory.create()

        assert client is not None
        assert client.id is not None
        assert client.name is not None
        assert client.email is not None
        assert client.phone is not None
        assert client.address is not None
        assert client.nit is not None
        assert client.is_active is True

    def test_create_client_with_custom_data(self, setup_factories):
        """Test de creación de cliente con datos personalizados."""
        # Crear cliente con datos específicos
        client = ClientFactory.create(
            name="Cliente Personalizado",
            email="custom@example.com"
        )

        assert client.id is not None
        assert client.name == "Cliente Personalizado"
        assert client.email == "custom@example.com"
        assert client.is_active is True

    def test_factory_data_consistency(self, setup_factories):
        """Test que verifica la consistencia de datos generados por factory."""
        client = ClientFactory.create()

        # Verificar que todos los campos tienen valores apropiados
        assert client.name is not None
        assert len(client.name) > 0
        assert client.email is not None
        assert "@" in client.email
        assert client.phone is not None
        assert client.address is not None
        assert client.nit is not None
        assert client.is_active is True

    def test_create_multiple_clients(self, setup_factories):
        """Test de creación de múltiples clientes."""
        # Crear 5 clientes usando batch
        clients = ClientFactory.create_batch(5)

        assert len(clients) == 5
        for client in clients:
            assert client.id is not None
            assert client.name is not None
            assert client.is_active is True
