"""
Tests para endpoints de productos.

Este test verifica los endpoints de productos: crear, obtener, editar y eliminar.
"""

from app.services.product_service import ProductService
from tests.factories import ProductFactory


class TestProductEndpoints:
    """Tests para endpoints de productos."""

    def test_create_product_endpoint(
            self,
            authenticated_client,
            db_session,
            sample_product_data):
        """Test del endpoint de crear producto."""
        response = authenticated_client.post(
            "/api/v1/products/", json=sample_product_data)

        assert response.status_code == 201
        product_data = response.json()
        assert product_data["name"] == sample_product_data["name"]
        assert product_data["description"] == sample_product_data["description"]
        assert product_data["price"] == sample_product_data["price"]
        assert product_data["stock"] == sample_product_data["stock"]
        assert product_data["sku"] == sample_product_data["sku"]
        assert product_data["is_active"] is True
        assert "id" in product_data
        assert "created_at" in product_data

        # Verificar que el producto se creó en la BD
        product_service = ProductService()
        db_product = product_service.get_product(
            db_session, product_data["id"])

        assert db_product is not None
        assert db_product.id == product_data["id"]
        assert db_product.name == sample_product_data["name"]
        assert db_product.price == sample_product_data["price"]
        assert db_product.stock == sample_product_data["stock"]
        assert db_product.sku == sample_product_data["sku"]

    def test_get_products_endpoint(
            self,
            authenticated_client,
            setup_factories):
        """Test del endpoint de obtener productos."""
        # Crear productos usando el factory
        ProductFactory.create(name="Product 1", price=10.99, stock=100)
        ProductFactory.create(name="Product 2", price=20.50, stock=50)

        # Obtener lista de productos
        response = authenticated_client.get("/api/v1/products/")

        assert response.status_code == 200
        products = response.json()
        assert len(products) == 2
        assert products[0]["name"] == "Product 1"
        assert products[1]["name"] == "Product 2"

    def test_update_product_endpoint(
            self,
            authenticated_client,
            setup_factories,
            db_session):
        """Test del endpoint de actualizar producto."""
        # Crear un producto usando el factory
        product = ProductFactory.create(
            name="Original Product",
            price=50.00,
            stock=100
        )
        product_id = product.id

        # Datos para actualizar
        update_data = {
            "name": "Updated Product",
            "price": 75.00,
            "stock": 150
        }

        # Actualizar el producto
        response = authenticated_client.put(
            f"/api/v1/products/{product_id}",
            json=update_data
        )

        assert response.status_code == 200
        updated_product = response.json()
        assert updated_product["name"] == "Updated Product"
        assert updated_product["price"] == 75.00
        assert updated_product["stock"] == 150

        # Verificar que se actualizó en la BD
        # Refrescar la sesión para ver los cambios del endpoint
        db_session.expire_all()
        product_service = ProductService()
        db_product = product_service.get_product(db_session, product_id)

        assert db_product.name == "Updated Product"
        assert db_product.price == 75.00
        assert db_product.stock == 150

    def test_delete_product_endpoint(
            self,
            authenticated_client,
            setup_factories,
            db_session):
        """Test del endpoint de eliminar producto (soft delete)."""
        # Crear un producto usando el factory
        product = ProductFactory.create(name="Product to Delete", price=30.00)
        product_id = product.id

        # Eliminar el producto
        response = authenticated_client.delete(
            f"/api/v1/products/{product_id}")

        assert response.status_code == 204

        # Verificar que el producto fue eliminado (soft delete)
        # Refrescar la sesión para ver los cambios del endpoint
        db_session.expire_all()
        product_service = ProductService()
        db_product = product_service.get_product(db_session, product_id)

        # El producto debe existir pero con is_active = False
        assert db_product is not None
        assert db_product.is_active is False

    def test_create_product_with_minimal_data(self, authenticated_client):
        """Test de creación de producto con datos mínimos."""
        minimal_data = {
            "name": "Minimal Product",
            "price": 19.99
        }

        response = authenticated_client.post(
            "/api/v1/products/", json=minimal_data)

        assert response.status_code == 201
        product_data = response.json()
        assert product_data["name"] == "Minimal Product"
        assert product_data["price"] == 19.99
        assert product_data["stock"] == 0  # Default
        assert product_data["description"] is None
        assert product_data["is_active"] is True
        # SKU debe ser generado automáticamente
        assert product_data["sku"] is not None
        assert product_data["sku"].startswith("PROD-")

    def test_create_product_without_authentication(
            self, client, sample_product_data):
        """Test de creación de producto sin autenticación (debería fallar)."""
        response = client.post("/api/v1/products/", json=sample_product_data)

        # FastAPI HTTPBearer devuelve 403 cuando no hay header de autenticación
        assert response.status_code == 403

    def test_get_product_by_id(self, authenticated_client, setup_factories):
        """Test del endpoint de obtener producto por ID."""
        # Crear un producto
        product = ProductFactory.create(name="Specific Product", price=45.00)

        # Obtener el producto por ID
        response = authenticated_client.get(f"/api/v1/products/{product.id}")

        assert response.status_code == 200
        product_data = response.json()
        assert product_data["id"] == product.id
        assert product_data["name"] == "Specific Product"
        assert product_data["price"] == 45.00

    def test_update_product_not_found(self, authenticated_client):
        """Test de actualizar producto que no existe."""
        update_data = {"name": "Updated Name"}

        response = authenticated_client.put(
            "/api/v1/products/99999", json=update_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_delete_product_not_found(self, authenticated_client):
        """Test de eliminar producto que no existe."""
        response = authenticated_client.delete("/api/v1/products/99999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
