import uuid

import pytest

from app.services.rag.document_store import chunk_text


def _payload(user_id, **overrides):
    data = {
        "message": "What does Project Firefly use for authentication?",
        "user_id": user_id,
        "history": [],
        "agent_override": "general_qa",
        "use_documents": True,
    }
    data.update(overrides)
    return data


def test_chunk_text_preserves_overlap_without_trailing_duplicate():
    words = [f"w{index}" for index in range(950)]
    chunks = chunk_text(" ".join(words), chunk_size=500, overlap=50)
    assert len(chunks) == 2
    assert chunks[0].split()[-50:] == chunks[1].split()[:50]


@pytest.mark.parametrize("chunk_size,overlap", [(0, 0), (100, -1), (100, 100)])
def test_chunk_text_rejects_invalid_configuration(chunk_size, overlap):
    with pytest.raises(ValueError):
        chunk_text("some text", chunk_size=chunk_size, overlap=overlap)


def test_document_upload_grounded_response_and_delete(client, auth_headers):
    user_id = f"rag-user-{uuid.uuid4()}"
    doc_id = f"doc-{uuid.uuid4()}"
    upload = client.post(
        "/api/chatbot/documents",
        headers=auth_headers,
        json={
            "doc_id": doc_id,
            "filename": "firefly-architecture.txt",
            "user_id": user_id,
            "text": (
                "Project Firefly uses rotating hardware-backed passkeys for authentication. "
                "Its audit service records every administrative change."
            ),
        },
    )
    assert upload.status_code == 200
    assert upload.json()["status"] == "indexed"
    assert upload.json()["chunks"] == 1

    grounded = client.post(
        "/api/chatbot/respond", headers=auth_headers, json=_payload(user_id)
    )
    assert grounded.status_code == 200
    body = grounded.json()
    assert body["sources"][0]["doc_id"] == doc_id
    assert body["sources"][0]["filename"] == "firefly-architecture.txt"
    assert "hardware-backed passkeys" in body["reply"]

    isolated = client.post(
        "/api/chatbot/respond",
        headers=auth_headers,
        json=_payload(f"other-{uuid.uuid4()}"),
    )
    assert isolated.status_code == 200
    assert isolated.json()["sources"] == []
    assert "couldn't find anything relevant" in isolated.json()["reply"]

    deleted = client.delete(
        f"/api/chatbot/documents/{doc_id}",
        params={"user_id": user_id},
        headers=auth_headers,
    )
    assert deleted.status_code == 200
    assert deleted.json() == {"status": "deleted", "doc_id": doc_id}


def test_document_routes_require_service_key(client):
    response = client.post(
        "/api/chatbot/documents",
        json={"doc_id": "x", "filename": "x.txt", "text": "text", "user_id": "u"},
    )
    assert response.status_code == 401


def test_document_delete_rejects_invalid_id(client, auth_headers):
    response = client.delete(
        "/api/chatbot/documents/not%20valid",
        params={"user_id": "user"},
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_agent_override_integration(client, auth_headers):
    response = client.post(
        "/api/chatbot/respond",
        headers=auth_headers,
        json=_payload(
            f"override-{uuid.uuid4()}",
            message="Explain a for loop",
            agent_override="coding_help",
            use_documents=False,
        ),
    )
    assert response.status_code == 200
    assert response.json()["agent"] == "coding_help"
    assert "for item in items" in response.json()["reply"]
