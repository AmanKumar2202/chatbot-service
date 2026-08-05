import pytest

from app.routes import chatbot as chatbot_routes
from app.services.agents import FormalWriterAgent
from app.services.analysis import (
    extract_action_items,
    extract_availability,
    extract_deadlines,
    generate_minutes,
)
from app.services.flashcards import generate_flashcards
from app.services.homework import help_with_essay, solve_math
from app.services.receipts import parse_receipt
from app.services.tools.argument_extractor import extract_arguments
from app.services.translation import UnsupportedLanguagePair, translate_text


MESSAGES = [
    {
        "id": "m1",
        "sender": "Aman",
        "content": "I will submit the report by tomorrow.",
    },
    {
        "id": "m2",
        "sender": "Maya",
        "content": "Friday afternoon or Monday morning works for me.",
    },
    {
        "id": "m3",
        "sender": "Lee",
        "content": "Maya, can you review the final draft by next Tuesday?",
    },
]


def test_flashcards_extract_definitions():
    cards = generate_flashcards(
        "Photosynthesis is the process by which plants convert light. "
        "Gravity means attraction between masses.",
        max_cards=5,
    )
    assert cards == [
        {
            "question": "What is Photosynthesis?",
            "answer": "process by which plants convert light",
        },
        {
            "question": "What is Gravity?",
            "answer": "attraction between masses",
        },
    ]


def test_flashcards_honestly_return_nothing_for_unusable_text():
    assert generate_flashcards("the and or.", max_cards=5) == []


def test_action_items_extract_owner_task_and_deadline():
    items = extract_action_items(MESSAGES)
    assert items[0]["owner"] == "Aman"
    assert items[0]["raw_deadline_phrase"] == "tomorrow"
    assert items[1]["owner"] == "Maya"
    assert items[1]["source_message_id"] == "m3"


def test_action_items_return_empty_when_no_assignment():
    assert extract_action_items(
        [{"id": "1", "sender": "A", "content": "The weather is pleasant."}]
    ) == []


def test_deadlines_require_time_and_deadline_context():
    assert extract_deadlines(MESSAGES) == [
        {
            "raw_time_phrase": "tomorrow",
            "context": "I will submit the report by tomorrow.",
            "source_message_id": "m1",
        },
        {
            "raw_time_phrase": "next Tuesday",
            "context": "Maya, can you review the final draft by next Tuesday?",
            "source_message_id": "m3",
        },
    ]
    assert extract_deadlines(
        [{"id": "1", "sender": "A", "content": "Tomorrow looks sunny."}]
    ) == []


def test_availability_extracts_all_phrases_by_sender():
    availability = extract_availability(MESSAGES)
    assert availability["Maya"] == ["Friday afternoon", "Monday morning"]


def test_meeting_minutes_combine_existing_extractors():
    result = generate_minutes(MESSAGES)
    assert result["attendees"] == ["Aman", "Maya", "Lee"]
    assert result["summary"]
    assert len(result["action_items"]) == 2
    assert len(result["deadlines"]) == 2


def test_math_equation_is_symbolically_solved():
    result = solve_math("solve 2x + 4 = 10")
    assert result["final_answer"] == "x = 3"
    assert result["is_generic_template"] is False
    assert len(result["steps"]) >= 2


def test_math_derivative_is_symbolically_computed():
    result = solve_math("derivative of x^3")
    assert result["final_answer"] == "3*x**2"


def test_essay_help_is_always_labeled_generic():
    result = help_with_essay("Compare renewable energy and fossil fuels")
    assert result["final_answer"] is None
    assert result["is_generic_template"] is True
    assert any("compare-contrast" in step for step in result["steps"])


def test_receipt_parser_extracts_balanced_receipt():
    result = parse_receipt(
        "Coffee 3.50\nBagel 4.00\nSubtotal 7.50\nTax 0.60\nTotal 8.10"
    )
    assert result["items"] == [
        {"name": "Coffee", "price": 3.5},
        {"name": "Bagel", "price": 4.0},
    ]
    assert result["parse_confidence"] == 1.0


def test_receipt_parser_flags_mismatched_ocr_as_low_confidence():
    result = parse_receipt(
        "Coffee 3.50\nBagel 4.00\nSubtotal 70.50\nTax 8.00\nTotal 99.99"
    )
    assert result["parse_confidence"] < 0.6


def test_receipt_parser_returns_empty_result_for_unusable_ocr():
    result = parse_receipt("blurred unreadable receipt")
    assert result["items"] == []
    assert result["parse_confidence"] == 0.0


def test_formal_writer_email_mode_includes_subject_and_body():
    result = FormalWriterAgent().handle(
        "write to HR regarding annual leave", [], mode="email"
    )
    assert result["subject"] == "Re: Annual Leave"
    assert "annual leave" in result["body"]


def test_citation_tool_extracts_topic():
    call = extract_arguments("find_citations", "find citations for renewable energy")
    assert call.arguments == {"topic": "renewable energy"}
    assert call.missing_arguments == []


def test_schedule_tool_extracts_multiple_options():
    call = extract_arguments(
        "match_schedule",
        "match our schedules for Friday afternoon or Monday morning",
    )
    assert call.arguments == {
        "availability_by_sender": {
            "requester": ["Friday afternoon", "Monday morning"]
        }
    }


@pytest.mark.parametrize(
    ("message", "intent", "tool_name"),
    [
        ("find citations for renewable energy", "find_citations", "find_citations"),
        (
            "match our schedules for Friday afternoon",
            "match_schedule",
            "match_schedule",
        ),
    ],
)
def test_new_tool_intents_route_through_chat_contract(
    client, auth_headers, message, intent, tool_name
):
    response = client.post(
        "/api/chatbot/respond",
        headers=auth_headers,
        json={"message": message, "user_id": f"{intent}-user", "history": []},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == intent
    assert body["tool_call"]["name"] == tool_name
    assert body["tool_call"]["missing_arguments"] == []


def test_translation_same_language_requires_no_pack():
    assert translate_text("hello", "en", "en") == "hello"


def test_translation_reports_uninstalled_pair():
    with pytest.raises(UnsupportedLanguagePair, match="Unsupported or uninstalled"):
        translate_text("hello", "zz", "yy")


def test_new_endpoints_require_authentication(client):
    for path, payload in [
        ("/api/chatbot/flashcards", {"text": "Gravity is a force."}),
        (
            "/api/chatbot/homework-help",
            {"prompt": "solve x + 1 = 2", "type": "math"},
        ),
        (
            "/api/chatbot/analyze",
            {"mode": "deadlines", "messages": MESSAGES},
        ),
        (
            "/api/chatbot/translate",
            {"text": "hello", "source_lang": "en", "target_lang": "en"},
        ),
        ("/api/chatbot/receipt/parse", {"ocr_text": "Coffee 3.50"}),
    ]:
        assert client.post(path, json=payload).status_code == 401


def test_feature_endpoints_return_structured_results(client, auth_headers):
    flashcards = client.post(
        "/api/chatbot/flashcards",
        headers=auth_headers,
        json={"text": "Gravity is a force that attracts masses.", "max_cards": 3},
    )
    assert flashcards.status_code == 200
    assert flashcards.json()["flashcards"][0]["question"] == "What is Gravity?"

    homework = client.post(
        "/api/chatbot/homework-help",
        headers=auth_headers,
        json={"prompt": "solve 2x + 4 = 10", "type": "math"},
    )
    assert homework.status_code == 200
    assert homework.json()["final_answer"] == "x = 3"

    analysis = client.post(
        "/api/chatbot/analyze",
        headers=auth_headers,
        json={"mode": "action_items", "messages": MESSAGES},
    )
    assert analysis.status_code == 200
    assert len(analysis.json()["result"]["action_items"]) == 2

    receipt = client.post(
        "/api/chatbot/receipt/parse",
        headers=auth_headers,
        json={"ocr_text": "Coffee 3.50\nSubtotal 3.50\nTotal 3.50"},
    )
    assert receipt.status_code == 200
    assert receipt.json()["parse_confidence"] == 1.0


def test_schedule_matching_preserves_participant_identity(client, auth_headers):
    response = client.post(
        "/api/chatbot/match-schedule",
        headers=auth_headers,
        json={
            "messages": [
                {"id": "m1", "sender": "u1", "content": "I am free tomorrow at 3pm"},
                {"id": "m2", "sender": "u2", "content": "Tomorrow at 3pm works"},
            ],
            "participants": [
                {"id": "u1", "name": "Aman", "timezone": "Asia/Calcutta"},
                {"id": "u2", "name": "Maya", "timezone": "UTC"},
            ],
        },
    )
    assert response.status_code == 200
    participants = response.json()["participants"]
    assert [participant["id"] for participant in participants] == ["u1", "u2"]
    assert all(participant["windows"] for participant in participants)


def test_supported_languages_endpoint_reflects_runtime_installation(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(
        "app.routes.chatbot.supported_languages",
        lambda: [{"code": "en", "name": "English"}],
    )
    response = client.get(
        "/api/chatbot/translate/supported-languages", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == {
        "languages": [{"code": "en", "name": "English"}]
    }


def test_analyze_minutes_deadlines_and_catch_up_modes(client, auth_headers):
    deadlines = client.post(
        "/api/chatbot/analyze",
        headers=auth_headers,
        json={"mode": "deadlines", "messages": MESSAGES},
    )
    assert len(deadlines.json()["result"]["deadlines"]) == 2

    minutes = client.post(
        "/api/chatbot/analyze",
        headers=auth_headers,
        json={"mode": "meeting_minutes", "messages": MESSAGES},
    )
    assert minutes.status_code == 200
    assert minutes.json()["result"]["attendees"] == ["Aman", "Maya", "Lee"]

    catch_up_messages = [
        {"id": str(index), "sender": "A", "content": sentence}
        for index, sentence in enumerate(
            [
                "The team reviewed the launch plan.",
                "The API migration is complete.",
                "Monitoring dashboards are now active.",
                "Documentation still needs review.",
                "The release remains scheduled for Friday.",
            ]
        )
    ]
    catch_up = client.post(
        "/api/chatbot/analyze",
        headers=auth_headers,
        json={"mode": "catch_up", "messages": catch_up_messages},
    )
    assert catch_up.status_code == 200
    assert len(catch_up.json()["result"]["bullet_points"]) == 3


def test_translate_endpoint_uses_local_translator(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(
        chatbot_routes,
        "translate_text",
        lambda text, source, target: f"{source}-{target}:{text}",
    )
    response = client.post(
        "/api/chatbot/translate",
        headers=auth_headers,
        json={"text": "hello", "source_lang": "en", "target_lang": "es"},
    )
    assert response.status_code == 200
    assert response.json() == {"translated_text": "en-es:hello"}
