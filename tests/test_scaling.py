import sys
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.core.rate_limit import limiter
from app.services.rag.document_store import (
    ChromaDocumentStore,
    DocumentQuotaExceeded,
    InMemoryDocumentStore,
)


def _chat(user_id: str) -> dict:
    return {"message": "hello", "user_id": user_id, "history": []}


def test_http_rate_limit_isolated_per_user(client, auth_headers):
    limiter._storage.reset()
    try:
        user_a = [
            client.post(
                "/api/chatbot/respond",
                headers=auth_headers,
                json=_chat("rate-user-a"),
            )
            for _ in range(61)
        ]
        user_b = client.post(
            "/api/chatbot/respond",
            headers=auth_headers,
            json=_chat("rate-user-b"),
        )
        assert user_a[-1].status_code == 429
        assert user_b.status_code == 200
    finally:
        limiter._storage.reset()


def test_document_quota_rejects_additional_document(monkeypatch):
    monkeypatch.setattr(settings, "rag_max_documents_per_user", 1)
    store = InMemoryDocumentStore()
    store.add_document("quota-user", "one", "one.txt", "first document")
    with pytest.raises(DocumentQuotaExceeded, match="document quota"):
        store.add_document("quota-user", "two", "two.txt", "second document")


def test_document_replacement_does_not_consume_another_quota(monkeypatch):
    monkeypatch.setattr(settings, "rag_max_documents_per_user", 1)
    store = InMemoryDocumentStore()
    store.add_document("quota-user", "one", "one.txt", "first document")
    assert store.add_document(
        "quota-user", "one", "updated.txt", "replacement document"
    ) == 1


def test_chroma_uses_shared_http_client(monkeypatch):
    sentinel = SimpleNamespace()
    calls = {}

    def http_client(**kwargs):
        calls.update(kwargs)
        return sentinel

    monkeypatch.setitem(sys.modules, "chromadb", SimpleNamespace(HttpClient=http_client))
    store = ChromaDocumentStore()
    assert store.client is sentinel
    assert calls["host"] == settings.rag_chroma_host
    assert calls["port"] == settings.rag_chroma_port


def test_general_deployment_rejects_rag_work(monkeypatch, client, auth_headers):
    monkeypatch.setattr(settings, "service_role", "general")
    response = client.post(
        "/api/chatbot/respond",
        headers=auth_headers,
        json={
            "message": "answer from my documents",
            "user_id": "role-user",
            "history": [],
            "use_documents": True,
        },
    )
    assert response.status_code == 503


def test_websocket_message_rate_limit_is_per_user(
    monkeypatch, client, auth_headers
):
    limiter._storage.reset()
    monkeypatch.setattr(settings, "websocket_message_rate_limit", "1/minute")
    service_key = auth_headers["X-Service-Key"]
    try:
        with client.websocket_connect(
            f"/api/chatbot/ws/chat?service_key={service_key}&user_id=ws-user"
        ) as websocket:
            websocket.send_json(_chat("ws-user"))
            assert websocket.receive_json()["intent"] == "greeting"
            websocket.send_json(_chat("ws-user"))
            assert websocket.receive_json()["error"] == "Message rate limit exceeded"
    finally:
        limiter._storage.reset()
