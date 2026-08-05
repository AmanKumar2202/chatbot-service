from typing import Any

from app.services.analysis.action_items import extract_action_items
from app.services.analysis.deadlines import extract_deadlines
from app.services.rag.summarizer import summarize


def generate_minutes(messages: list[dict[str, Any]]) -> dict[str, Any]:
    full_text = " ".join(str(message["content"]) for message in messages)
    summary = summarize(full_text, num_sentences=5)
    attendees = list(dict.fromkeys(str(message["sender"]) for message in messages))
    return {
        "attendees": attendees,
        "summary": summary["summary"],
        "action_items": extract_action_items(messages),
        "deadlines": extract_deadlines(messages),
    }
