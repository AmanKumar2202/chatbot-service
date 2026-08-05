import pytest

from app.core.rate_limit import limiter
from app.services.rag.summarizer import split_into_sentences, summarize


def test_short_summary_returns_original_text():
    text = "First fact. Second fact."
    result = summarize(text, num_sentences=5)
    assert result == {
        "summary": text,
        "key_points": ["First fact.", "Second fact."],
    }


def test_long_summary_has_requested_count_in_document_order():
    text = (
        "Mercury is closest to the sun. Venus has a thick atmosphere. "
        "Earth has liquid water. Mars is known as the red planet. "
        "Jupiter is the largest planet. Saturn has prominent rings."
    )
    result = summarize(text, num_sentences=3)
    assert len(result["key_points"]) == 3
    positions = [text.index(sentence) for sentence in result["key_points"]]
    assert positions == sorted(positions)
    assert split_into_sentences(result["summary"]) == result["key_points"]


def test_summarize_endpoint_requires_authentication(client):
    response = client.post(
        "/api/chatbot/summarize",
        json={"text": "One sentence.", "num_sentences": 1},
    )
    assert response.status_code == 401


def test_summarize_endpoint_returns_extracts(client, auth_headers):
    response = client.post(
        "/api/chatbot/summarize",
        headers=auth_headers,
        json={"text": "One sentence. Another sentence.", "num_sentences": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["key_points"]) == 1
    assert body["summary"] == body["key_points"][0]


def test_summarize_endpoint_rejects_oversized_text(client, auth_headers):
    response = client.post(
        "/api/chatbot/summarize",
        headers=auth_headers,
        json={"text": "x" * 2_000_001},
    )
    assert response.status_code == 422


def test_summarize_endpoint_is_rate_limited(client, auth_headers):
    limiter._storage.reset()
    try:
        responses = [
            client.post(
                "/api/chatbot/summarize",
                headers=auth_headers,
                json={"text": "A short sentence.", "num_sentences": 1},
            )
            for _ in range(61)
        ]
        assert responses[-1].status_code == 429
    finally:
        limiter._storage.reset()

