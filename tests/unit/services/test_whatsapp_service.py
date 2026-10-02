# -*- coding: utf-8 -*-
"""
Unit tests for WhatsAppService.send_document error classification.

EvolutionAPI is simulated with httpx.MockTransport — no real network calls are made.
"""
from io import BytesIO

import httpx
import pytest

from app.services import whatsapp_service as whatsapp_module
from app.services.whatsapp_service import (
    WhatsAppDisconnectedError,
    WhatsAppService,
    WhatsAppUnavailableError,
)


def _make_service(monkeypatch, handler) -> WhatsAppService:
    real_client = httpx.Client
    monkeypatch.setattr(
        whatsapp_module.httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    service = WhatsAppService()
    service.api_url = "https://evolution.test"
    service.api_key = "test-key"
    return service


def _send(service: WhatsAppService) -> dict:
    return service.send_document(
        to="50212345678",
        file_buffer=BytesIO(b"%PDF-1.4"),
        filename="comprobante.pdf",
        instance_name="tenant_test",
    )


def test_send_document_returns_response_on_success(monkeypatch):
    service = _make_service(monkeypatch, lambda request: httpx.Response(201, json={"key": {"id": "abc"}}))

    assert _send(service) == {"key": {"id": "abc"}}


def test_send_document_raises_disconnected_when_session_closed(monkeypatch):
    body = {"status": 500, "error": "Internal Server Error", "response": {"message": "Connection Closed"}}
    service = _make_service(monkeypatch, lambda request: httpx.Response(500, json=body))

    with pytest.raises(WhatsAppDisconnectedError):
        _send(service)


def test_send_document_raises_unavailable_on_other_http_error(monkeypatch):
    service = _make_service(monkeypatch, lambda request: httpx.Response(500, json={"error": "boom"}))

    with pytest.raises(WhatsAppUnavailableError):
        _send(service)


def test_send_document_raises_unavailable_on_network_error(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("[Errno -3] Temporary failure in name resolution", request=request)

    service = _make_service(monkeypatch, handler)

    with pytest.raises(WhatsAppUnavailableError):
        _send(service)
