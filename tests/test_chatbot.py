import pytest
import uuid

from app.core.config import settings
from app.ml.predictor import Prediction, predict_intent
from app.ml.model_loader import ModelArtifactError, _validate_metadata, model_metadata
from app.services import ai_engine
from app.services.generator import extract_formal_details, extract_topic
from app.routes.chatbot import _stream_chunks
from app.routes import chatbot as chatbot_routes
from app.models.schemas import ChatRequest


def request_body(message="hello", history=None, user_id="test-user"):
    return {"message": message, "user_id": user_id, "history": history or []}


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("write a paragraph about technology", "paragraph"),
        ("write a formal message to HR regarding leave", "formal"),
        ("hello there", "greeting"),
        ("what can you do", "help"),
        ("this is not working", "error"),
        ("see you later", "bye"),
        ("explain a python for loop", "code_help"),
        ("book a meeting about planning tomorrow at 3pm", "book_meeting"),
        ("search the web for FastAPI documentation", "web_search"),
        ("find citations for renewable energy", "find_citations"),
        ("match our schedules for Friday afternoon", "match_schedule"),
    ],
)
def test_intent_classification(text, expected):
    prediction = predict_intent(text)
    assert prediction.intent == expected
    assert 0 <= prediction.confidence <= 1


def test_extract_formal_details_separates_recipient_and_action():
    assert extract_formal_details(
        "write a formal message to my manager for annual leave"
    ) == ("My Manager", "annual leave")


def test_extract_formal_details_requires_action():
    assert extract_formal_details("write a formal message to manager") is None


def test_extract_topic():
    assert extract_topic("Please write about renewable energy.") == "renewable energy"


def test_extract_topic_does_not_match_inside_words():
    assert extract_topic("Security protects systems from common attacks.") is None


def test_low_confidence_uses_clarification(monkeypatch):
    monkeypatch.setattr(
        ai_engine,
        "predict_intent",
        lambda _: Prediction(intent="paragraph", confidence=0.1),
    )
    result = ai_engine.generate_reply("ambiguous words", [])
    assert result.intent == "clarify"


def test_follow_up_reuses_previous_topic():
    result = ai_engine.generate_reply(
        "tell me more",
        [{"role": "user", "content": "write about cybersecurity"}],
    )
    assert result.intent == "paragraph"
    assert "Cybersecurity" in result.text


@pytest.mark.parametrize("message", ["", "   "])
def test_empty_message_rejected(client, auth_headers, message):
    response = client.post(
        "/api/chatbot/respond", json=request_body(message), headers=auth_headers
    )
    assert response.status_code == 422


def test_oversized_message_rejected(client, auth_headers):
    response = client.post(
        "/api/chatbot/respond",
        json=request_body("x" * (settings.max_message_length + 1)),
        headers=auth_headers,
    )
    assert response.status_code == 422


def test_invalid_agent_override_rejected(client, auth_headers):
    body = request_body("hello")
    body["agent_override"] = "unknown_agent"
    response = client.post("/api/chatbot/respond", json=body, headers=auth_headers)
    assert response.status_code == 422


def test_authentication_required(client):
    response = client.post("/api/chatbot/respond", json=request_body())
    assert response.status_code == 401


def test_chat_happy_path(client, auth_headers):
    response = client.post(
        "/api/chatbot/respond",
        json=request_body("write a paragraph about cybersecurity"),
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["intent"] == "paragraph"
    assert response.json()["reply"]
    assert response.json()["agent"] == "general_qa"
    assert response.json()["tool_call"] is None
    assert response.json()["sources"] == []


def test_structured_history_contract_and_follow_up(client, auth_headers):
    response = client.post(
        "/api/chatbot/respond",
        json=request_body(
            "tell me more",
            history=[
                {"role": "user", "content": "write about renewable energy"},
                {"role": "assistant", "content": "Renewable energy comes from natural sources."},
            ],
        ),
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["intent"] == "paragraph"
    assert "Renewable energy" in response.json()["reply"]


def test_history_is_stateless_and_must_be_supplied_by_caller(client, auth_headers):
    user_id = f"history-{uuid.uuid4()}"
    first = client.post(
        "/api/chatbot/respond",
        json=request_body("write about cybersecurity", user_id=user_id),
        headers=auth_headers,
    )
    assert first.status_code == 200
    follow_up = client.post(
        "/api/chatbot/respond",
        json=request_body("tell me more", user_id=user_id),
        headers=auth_headers,
    )
    assert follow_up.status_code == 200
    assert "Cybersecurity" not in follow_up.json()["reply"]


def test_non_contextual_request_does_not_require_server_history():
    response = chatbot_routes._respond(
        ChatRequest(message="hello there", user_id=f"fast-{uuid.uuid4()}")
    )
    assert response.intent == "greeting"


def test_stream_contract(client, auth_headers):
    with client.stream(
        "POST",
        "/api/chatbot/stream",
        json=request_body("hello there", user_id="stream-user"),
        headers=auth_headers,
    ) as response:
        body = "".join(response.iter_text())
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = [
        line.removeprefix("data: ")
        for line in body.splitlines()
        if line.startswith("data: ")
    ]
    assert any('"delta"' in event for event in events)
    assert '"done": true' in events[-1]
    assert '"intent": "greeting"' in events[-1]
    assert '"agent": "smalltalk"' in events[-1]


def test_stream_chunks_preserve_content_and_reduce_event_count():
    text = "First line.\nSecond line with several words."
    chunks = _stream_chunks(text)
    assert "".join(chunks) == text
    assert len(chunks) < len(text.split())


def test_request_id_is_echoed(client, auth_headers):
    response = client.post(
        "/api/chatbot/respond",
        json=request_body("hello", user_id="request-id-user"),
        headers={**auth_headers, "X-Request-Id": "upstream-request-123"},
    )
    assert response.headers["X-Request-Id"] == "upstream-request-123"
    assert float(response.headers["X-Response-Time-Ms"]) >= 0


def test_health_and_readiness(client):
    assert client.get("/health").json() == {"status": "alive"}
    assert client.get("/ready").json() == {"ready": True, "rag_ready": True}


def test_metrics_endpoint_is_exposed(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text


def test_hard_request_body_limit(client, auth_headers):
    response = client.post(
        "/api/chatbot/respond",
        headers=auth_headers,
        content=b"x" * (settings.max_request_body_bytes + 1),
    )
    assert response.status_code == 413


def test_model_artifacts_have_verified_training_metadata(client):
    client.get("/ready")
    metadata = model_metadata()
    assert metadata is not None
    assert metadata["training_examples"] == 600
    assert metadata["feature_count"] > 0
    assert len(metadata["dataset_sha256"]) == 64
    assert set(metadata["classes"]) == {
        "paragraph", "formal", "greeting", "help", "error", "bye",
        "code_help", "book_meeting", "web_search", "set_reminder",
        "find_citations", "match_schedule",
    }


def test_tampered_model_metadata_is_rejected(client):
    client.get("/ready")
    tampered = model_metadata()
    tampered["model_sha256"] = "0" * 64
    with pytest.raises(ModelArtifactError, match="Stale or corrupt"):
        _validate_metadata(tampered)
