# -*- coding: utf-8 -*-
"""
Tests for GET /api/v1/orders/analytics/products-summary endpoint.

Covers:
- Response shape and 200 status
- Unauthenticated request
- Empty result when no matching orders
- Exclusion of orders without route
- route_id filter
- status_filter filter
- date_from / date_to filters
- Invalid status returns 400
- Invalid date range returns 400
"""

import pytest
from app.models.order import OrderStatus

SUMMARY_URL = "/api/v1/orders/analytics/products-summary"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def route_in_db(setup_factories):
    from tests.factories import RouteFactory
    return RouteFactory.create(name="Ruta Norte")


@pytest.fixture
def product_in_db(setup_factories):
    from tests.factories import ProductFactory
    return ProductFactory.create(name="Queso Fresco", price=30.0, stock=100, is_active=True)


@pytest.fixture
def order_with_route(setup_factories, route_in_db):
    """PENDING order with a route and one item."""
    from tests.factories import ClientFactory, OrderFactory, OrderItemFactory, ProductFactory
    client = ClientFactory.create()
    product = ProductFactory.create(price=30.0, stock=100, is_active=True)
    order = OrderFactory.create(
        client=client,
        route=route_in_db,
        status=OrderStatus.PENDING,
        total_amount=150.0,
    )
    OrderItemFactory.create(order=order, product=product, quantity=5, unit_price=30.0, total_price=150.0)
    return order


@pytest.fixture
def order_without_route(setup_factories):
    """Order with route=None — should be excluded from the summary."""
    from tests.factories import ClientFactory, OrderFactory, OrderItemFactory, ProductFactory
    client = ClientFactory.create()
    product = ProductFactory.create(price=30.0, stock=100, is_active=True)
    order = OrderFactory.create(
        client=client,
        route=None,
        status=OrderStatus.PENDING,
        total_amount=90.0,
    )
    OrderItemFactory.create(order=order, product=product, quantity=3, unit_price=30.0, total_price=90.0)
    return order


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestProductsSummaryShape:

    def test_returns_200_with_correct_shape(self, authenticated_client, test_user, order_with_route):
        response = authenticated_client.get(SUMMARY_URL)
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert "grand_total_value" in data
        assert "total_order_count" in data
        assert "route_name" in data
        assert isinstance(data["products"], list)

    def test_product_item_has_correct_fields(self, authenticated_client, test_user, order_with_route):
        response = authenticated_client.get(SUMMARY_URL)
        assert response.status_code == 200
        products = response.json()["products"]
        assert len(products) >= 1
        item = products[0]
        assert "product_id" in item
        assert "product_name" in item
        assert "total_quantity" in item
        assert "total_value" in item

    def test_unauthenticated_returns_4xx(self, client):
        response = client.get(SUMMARY_URL)
        assert response.status_code in (401, 403)


class TestProductsSummaryFiltering:

    def test_empty_result_returns_200_not_404(self, authenticated_client, test_user, setup_factories):
        """No matching data should return empty list with 200, not 404."""
        response = authenticated_client.get(SUMMARY_URL, params={"status_filter": "delivered"})
        assert response.status_code == 200
        data = response.json()
        assert data["products"] == []
        assert data["grand_total_value"] == 0.0
        assert data["total_order_count"] == 0

    def test_excludes_orders_without_route(
        self, authenticated_client, test_user, order_without_route
    ):
        """Orders with route_id=None must not appear in the summary."""
        response = authenticated_client.get(SUMMARY_URL)
        assert response.status_code == 200
        data = response.json()
        assert data["products"] == []
        assert data["total_order_count"] == 0

    def test_includes_orders_with_route(
        self, authenticated_client, test_user, order_with_route
    ):
        response = authenticated_client.get(SUMMARY_URL)
        assert response.status_code == 200
        data = response.json()
        assert len(data["products"]) >= 1
        assert data["total_order_count"] >= 1

    def test_route_id_filter_scopes_to_one_route(
        self, authenticated_client, test_user, setup_factories, route_in_db
    ):
        from tests.factories import ClientFactory, RouteFactory, OrderFactory, OrderItemFactory, ProductFactory

        # Orden en la ruta bajo prueba
        client_a = ClientFactory.create()
        product_a = ProductFactory.create(price=10.0, stock=100, is_active=True)
        order_a = OrderFactory.create(client=client_a, route=route_in_db, status=OrderStatus.PENDING, total_amount=50.0)
        OrderItemFactory.create(order=order_a, product=product_a, quantity=5, unit_price=10.0, total_price=50.0)

        # Orden en otra ruta
        other_route = RouteFactory.create(name="Ruta Sur")
        client_b = ClientFactory.create()
        product_b = ProductFactory.create(price=20.0, stock=100, is_active=True)
        order_b = OrderFactory.create(client=client_b, route=other_route, status=OrderStatus.PENDING, total_amount=100.0)
        OrderItemFactory.create(order=order_b, product=product_b, quantity=5, unit_price=20.0, total_price=100.0)

        response = authenticated_client.get(SUMMARY_URL, params={"route_id": route_in_db.id})
        assert response.status_code == 200
        data = response.json()

        # Solo debe aparecer el producto de route_in_db
        product_ids = [p["product_id"] for p in data["products"]]
        assert product_a.id in product_ids
        assert product_b.id not in product_ids
        assert data["route_name"] == route_in_db.name

    def test_route_name_is_none_when_no_route_filter(
        self, authenticated_client, test_user, order_with_route
    ):
        response = authenticated_client.get(SUMMARY_URL)
        assert response.status_code == 200
        assert response.json()["route_name"] is None

    def test_status_filter_scopes_results(
        self, authenticated_client, test_user, setup_factories, route_in_db
    ):
        from tests.factories import ClientFactory, OrderFactory, OrderItemFactory, ProductFactory

        # Orden DELIVERED
        client = ClientFactory.create()
        product = ProductFactory.create(price=50.0, stock=100, is_active=True)
        order = OrderFactory.create(
            client=client, route=route_in_db,
            status=OrderStatus.DELIVERED, total_amount=100.0
        )
        OrderItemFactory.create(order=order, product=product, quantity=2, unit_price=50.0, total_price=100.0)

        # Filtrar por PENDING no debe devolver nada
        response = authenticated_client.get(SUMMARY_URL, params={"status_filter": "pending"})
        assert response.status_code == 200
        assert response.json()["products"] == []

        # Filtrar por DELIVERED debe devolver el producto
        response = authenticated_client.get(SUMMARY_URL, params={"status_filter": "delivered"})
        assert response.status_code == 200
        assert len(response.json()["products"]) >= 1

    def test_quantity_totals_are_aggregated_correctly(
        self, authenticated_client, test_user, setup_factories, route_in_db
    ):
        """Two orders with the same product on the same route must sum quantities."""
        from tests.factories import ClientFactory, OrderFactory, OrderItemFactory, ProductFactory

        product = ProductFactory.create(name="Queso Duro", price=25.0, stock=200, is_active=True)

        for _ in range(2):
            client = ClientFactory.create()
            order = OrderFactory.create(client=client, route=route_in_db, status=OrderStatus.PENDING, total_amount=250.0)
            OrderItemFactory.create(order=order, product=product, quantity=10, unit_price=25.0, total_price=250.0)

        response = authenticated_client.get(SUMMARY_URL)
        assert response.status_code == 200
        products = response.json()["products"]
        match = next((p for p in products if p["product_id"] == product.id), None)
        assert match is not None
        assert match["total_quantity"] == pytest.approx(20.0)


class TestProductsSummaryValidation:

    def test_invalid_status_returns_400(self, authenticated_client, test_user):
        response = authenticated_client.get(SUMMARY_URL, params={"status_filter": "invalid_status"})
        assert response.status_code == 400

    def test_invalid_date_range_returns_400(self, authenticated_client, test_user):
        response = authenticated_client.get(
            SUMMARY_URL,
            params={"date_from": "2026-06-20", "date_to": "2026-06-01"},
        )
        assert response.status_code == 400
