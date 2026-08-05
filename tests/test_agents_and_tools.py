import pytest

from app.services.agents import (
    CodingHelpAgent,
    FormalWriterAgent,
    GeneralQAAgent,
    SmalltalkAgent,
)
from app.services.ai_engine import generate_reply
from app.services.tools.argument_extractor import extract_arguments


def test_coding_agent_matches_known_concept():
    reply = CodingHelpAgent().handle("Explain a Python for loop", [])
    assert "for item in items" in reply


def test_coding_agent_clarifies_unknown_concept():
    reply = CodingHelpAgent().handle("help with my program", [])
    assert "which programming language or concept" in reply


def test_general_agent_uses_history():
    reply = GeneralQAAgent().handle(
        "tell me more",
        [{"role": "user", "content": "explain cybersecurity"}],
    )
    assert "Cybersecurity" in reply


def test_formal_agent_generates_message():
    reply = FormalWriterAgent().handle("write to HR regarding annual leave", [])
    assert "Dear Hr" in reply or "Hello Hr" in reply
    assert "annual leave" in reply


def test_smalltalk_agent_uses_requested_intent():
    assert SmalltalkAgent("bye").handle("bye", [])


def test_meeting_argument_extraction():
    call = extract_arguments(
        "book_meeting", "book a meeting about roadmap planning tomorrow at 3pm"
    )
    assert call.arguments == {
        "topic": "roadmap planning",
        "time_reference": "tomorrow at 3pm",
    }
    assert call.missing_arguments == []


def test_meeting_missing_arguments_are_explicit():
    call = extract_arguments("book_meeting", "book a meeting tomorrow")
    assert call.arguments == {"time_reference": "tomorrow"}
    assert call.missing_arguments == ["topic"]


def test_search_argument_extraction():
    call = extract_arguments("web_search", "please search the web for FastAPI docs")
    assert call.arguments == {"query": "FastAPI docs"}
    assert call.missing_arguments == []


def test_search_missing_query():
    call = extract_arguments("web_search", "search for")
    assert call.arguments == {}
    assert call.missing_arguments == ["query"]


def test_reminder_argument_extraction():
    call = extract_arguments("set_reminder", "remind me tomorrow to call the bank")
    assert call.arguments == {"time": "tomorrow", "message": "call the bank"}
    assert call.missing_arguments == []


def test_reminder_missing_time():
    call = extract_arguments("set_reminder", "remind me to call the bank")
    assert call.arguments == {"message": "call the bank"}
    assert call.missing_arguments == ["time"]


def test_reminder_missing_content():
    call = extract_arguments("set_reminder", "remind me in 2 hours")
    assert call.arguments == {"time": "in 2 hours"}
    assert call.missing_arguments == ["message"]


def test_reminder_missing_time_and_content():
    call = extract_arguments("set_reminder", "remind me")
    assert call.arguments == {}
    assert call.missing_arguments == ["message", "time"]


def test_tool_history_routes_to_confirmation():
    result = generate_reply(
        "thanks",
        [{"role": "tool", "content": "Meeting created with id abc-123"}],
    )
    assert result.agent == "tool_router"
    assert result.intent == "tool_result"
    assert "abc-123" in result.text


def test_fullstack_confirmation_prompt_consumes_json_tool_result_honestly():
    result = generate_reply(
        "Present the tool result clearly and accurately. Do not claim success unless the tool result says it succeeded.",
        [
            {
                "role": "tool",
                "content": '{"tool":"web_search","status":"unavailable","error":"timeout"}',
            }
        ],
    )
    assert result.agent == "tool_router"
    assert result.intent == "tool_result"
    assert "did not complete successfully" in result.text


def test_tool_history_does_not_hijack_unrelated_new_request():
    result = generate_reply(
        "explain a python for loop",
        [{"role": "tool", "content": "Meeting created"}],
    )
    assert result.agent == "coding_help"


def test_scheduled_reminder_tool_result_uses_resolved_time():
    result = generate_reply(
        "anything",
        [
            {
                "role": "tool",
                "content": (
                    '{"status":"scheduled",'
                    '"remind_at":"2026-07-28T15:00:00Z"}'
                ),
            }
        ],
    )
    assert result.agent == "tool_router"
    assert result.intent == "tool_result"
    assert "2026-07-28T15:00:00Z" in result.text


def test_tool_call_contract_integration(client, auth_headers):
    response = client.post(
        "/api/chatbot/respond",
        headers=auth_headers,
        json={
            "message": "book a meeting about roadmap planning tomorrow at 3pm",
            "user_id": "tool-user",
            "history": [],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["agent"] == "tool_router"
    assert body["intent"] == "book_meeting"
    assert body["tool_call"] == {
        "name": "book_meeting",
        "arguments": {
            "topic": "roadmap planning",
            "time_reference": "tomorrow at 3pm",
        },
        "missing_arguments": [],
    }


def test_reminder_tool_call_contract_integration(client, auth_headers):
    response = client.post(
        "/api/chatbot/respond",
        headers=auth_headers,
        json={
            "message": "remind me tomorrow to call the bank",
            "user_id": "reminder-user",
            "history": [],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "set_reminder"
    assert body["tool_call"] == {
        "name": "set_reminder",
        "arguments": {"message": "call the bank", "time": "tomorrow"},
        "missing_arguments": [],
    }


@pytest.mark.parametrize(
    ("override", "expected_agent"),
    [
        ("coding_help", "coding_help"),
        ("general_qa", "general_qa"),
        ("formal_writer", "formal_writer"),
        ("smalltalk", "smalltalk"),
    ],
)
def test_agent_override(override, expected_agent):
    result = generate_reply(
        "explain a loop" if override != "formal_writer" else "write to HR about leave",
        [],
        override,
    )
    assert result.agent == expected_agent
    assert result.confidence == 1.0
