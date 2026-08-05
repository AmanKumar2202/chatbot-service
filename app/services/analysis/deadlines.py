import re
from typing import Any

from app.services.tools.argument_extractor import find_time_phrase


DEADLINE_CONTEXT = re.compile(
    r"\b(?:due|deadline|by|submit|finish|complete|deliver|before)\b",
    re.IGNORECASE,
)


def extract_deadline_phrase(text: str) -> str | None:
    return find_time_phrase(text) if DEADLINE_CONTEXT.search(text) else None


def extract_deadlines(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    deadlines: list[dict[str, str]] = []
    for message in messages:
        content = str(message["content"])
        phrase = extract_deadline_phrase(content)
        if phrase:
            deadlines.append(
                {
                    "raw_time_phrase": phrase,
                    "context": content,
                    "source_message_id": str(message["id"]),
                }
            )
    return deadlines
