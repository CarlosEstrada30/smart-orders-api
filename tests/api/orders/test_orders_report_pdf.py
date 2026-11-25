# -*- coding: utf-8 -*-
"""
Tests del rango de fechas por defecto en GET /api/v1/orders/report/pdf.

Si no se envía date_from ni date_to, el reporte se limita a los últimos 30 días
para no cargar todo el historial en memoria.
"""

from datetime import date, timedelta

import pytest
from fastapi import HTTPException

from app.api.v1 import orders as orders_module
from app.models.order import OrderStatus
from app.utils.timezone import get_current_time_in_timezone

REPORT_URL = "/api/v1/orders/report/pdf"


@pytest.fixture
def captured_dates(monkeypatch):
    """Captura las fechas que recibe la consulta y corta el request con 404."""
    captured = {}

    def fake_get_report_orders(order_service, db, status_enum, route_id,
                               date_from, date_to, search, **kwargs):
        captured["date_from"] = date_from
        captured["date_to"] = date_to
        captured["route_id"] = route_id
        raise HTTPException(status_code=404, detail="Orders not found")

    monkeypatch.setattr(
        orders_module, "_get_report_orders", fake_get_report_orders)
    return captured


class TestOrdersReportDefaultDateRange:
    def test_report_without_dates_uses_last_30_days(
            self, authenticated_client, captured_dates):
        response = authenticated_client.get(
            REPORT_URL,
            headers={**authenticated_client.headers,
                     "X-Timezone": "America/Guatemala"},
        )

        assert response.status_code == 404
        today = get_current_time_in_timezone("America/Guatemala").date()
        assert captured_dates["date_to"] == today
        assert captured_dates["date_from"] == today - timedelta(days=29)

    def test_report_with_route_but_no_dates_uses_last_30_days(
            self, authenticated_client, captured_dates):
        response = authenticated_client.get(f"{REPORT_URL}?route_id=3")

        assert response.status_code == 404
        assert captured_dates["route_id"] == 3
        span = captured_dates["date_to"] - captured_dates["date_from"]
        assert span == timedelta(days=29)

    def test_report_with_explicit_dates_keeps_them(
            self, authenticated_client, captured_dates):
        response = authenticated_client.get(
            f"{REPORT_URL}?date_from=2026-01-01&date_to=2026-06-30")

        assert response.status_code == 404
        assert captured_dates["date_from"] == date(2026, 1, 1)
        assert captured_dates["date_to"] == date(2026, 6, 30)

    def test_report_with_only_date_from_is_not_modified(
            self, authenticated_client, captured_dates):
        response = authenticated_client.get(f"{REPORT_URL}?date_from=2026-11-01")

        assert response.status_code == 404
        assert captured_dates["date_from"] == date(2026, 11, 1)
        assert captured_dates["date_to"] is None


class TestOrdersReportGeneration:
    """Genera el PDF real con órdenes de prueba (sin mocks de la consulta)."""

    @pytest.fixture
    def report_data(self, setup_factories, db_session):
        from app.models.settings import Settings

        db_session.add(Settings(
            company_name="Empresa Test", business_name="Empresa Test S.A.",
            nit="123456-7", phone="5555-5555"))
        db_session.commit()

        route = setup_factories.RouteFactory.create()
        product = setup_factories.ProductFactory.create()
        active_orders = []
        for status in (OrderStatus.PENDING, OrderStatus.CONFIRMED):
            order = setup_factories.OrderFactory.create(route=route, status=status)
            setup_factories.OrderItemFactory.create(order=order, product=product)
            active_orders.append(order)
        cancelled = setup_factories.OrderFactory.create(
            route=route, status=OrderStatus.CANCELLED)
        setup_factories.OrderItemFactory.create(order=cancelled, product=product)
        return route, active_orders, cancelled

    @pytest.fixture
    def captured_report_orders(self, monkeypatch):
        """Espía las órdenes que recibe el generador del PDF."""
        from app.services.orders_report_generator import OrdersReportGenerator

        captured = {}
        original = OrdersReportGenerator.generate_report_buffer

        def spy(self, orders, *args, **kwargs):
            captured["orders"] = list(orders)
            return original(self, orders, *args, **kwargs)

        monkeypatch.setattr(OrdersReportGenerator, "generate_report_buffer", spy)
        return captured

    def test_report_returns_pdf_without_cancelled_orders(
            self, authenticated_client, report_data, captured_report_orders):
        route, active_orders, cancelled = report_data

        response = authenticated_client.get(f"{REPORT_URL}?route_id={route.id}")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF")
        report_ids = {o.id for o in captured_report_orders["orders"]}
        assert report_ids == {o.id for o in active_orders}
        assert cancelled.id not in report_ids

    def test_report_with_cancelled_status_filter_includes_cancelled(
            self, authenticated_client, report_data, captured_report_orders):
        route, _, cancelled = report_data

        response = authenticated_client.get(
            f"{REPORT_URL}?route_id={route.id}&status_filter=cancelled")

        assert response.status_code == 200
        report_ids = {o.id for o in captured_report_orders["orders"]}
        assert report_ids == {cancelled.id}
