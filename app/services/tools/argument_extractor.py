import re
from dataclasses import dataclass
from typing import Any

from app.services.tools.tool_registry import TOOL_REGISTRY


@dataclass(frozen=True)
class ExtractedToolCall:
    name: str
    arguments: dict[str, Any]
    missing_arguments: list[str]


TIME_PATTERNS = [
    r"\btomorrow(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?\b",
    r"\bnext\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?\b",
    r"\btoday(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?\b",
    r"\bin\s+\d+\s+(?:minutes?|hours?|days?)\b",
    r"\bon\s+\d{4}-\d{2}-\d{2}(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)?\b",
    r"\bat\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)\b",
    r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)"
    r"(?:\s+(?:morning|afternoon|evening|night))?\b",
    r"\b(?:this|next)\s+(?:morning|afternoon|evening|week|weekend)\b",
]


def find_all_time_phrases(message: str) -> list[str]:
    matches: list[tuple[int, str]] = []
    occupied: list[tuple[int, int]] = []
    for pattern in TIME_PATTERNS:
        for match in re.finditer(pattern, message, flags=re.IGNORECASE):
            span = match.span()
            if any(span[0] < end and span[1] > start for start, end in occupied):
                continue
            occupied.append(span)
            matches.append((span[0], match.group(0).strip()))
    return [value for _, value in sorted(matches)]


def find_time_phrase(message: str) -> str | None:
    phrases = find_all_time_phrases(message)
    return phrases[0] if phrases else None


def _meeting_arguments(message: str) -> dict[str, str]:
    arguments: dict[str, str] = {}
    topic_match = re.search(
        r"\b(?:about|regarding)\s+(.+?)(?=\s+(?:tomorrow|today|next\s+\w+|in\s+\d+|on\s+\d{4}-\d{2}-\d{2}|at\s+\d)|[?.!,]|$)",
        message,
        flags=re.IGNORECASE,
    )
    if topic_match:
        arguments["topic"] = topic_match.group(1).strip()
    time_phrase = find_time_phrase(message)
    if time_phrase:
        arguments["time_reference"] = time_phrase
    return arguments


def _search_arguments(message: str) -> dict[str, str]:
    query = re.sub(
        r"^\s*(?:please\s+)?(?:search(?:\s+the\s+web)?\s+for|look\s+up|find\s+(?:information\s+)?about|web\s+search(?:\s+for)?)\s*",
        "",
        message,
        flags=re.IGNORECASE,
    ).strip(" .?!")
    return {"query": query} if query and query.casefold() != message.strip(" .?!").casefold() else {}


def extract_reminder_args(message: str) -> dict[str, str]:
    arguments: dict[str, str] = {}
    time_match = None
    for pattern in TIME_PATTERNS:
        time_match = re.search(pattern, message, flags=re.IGNORECASE)
        if time_match:
            arguments["time"] = time_match.group(0).strip()
            break

    if time_match:
        remainder = message[time_match.end() :]
        content_match = re.search(
            r"^\s*(?:,?\s*)?(?:to|about|that)\s+(.+?)\s*[?.!]*$",
            remainder,
            flags=re.IGNORECASE,
        )
        if content_match:
            content = content_match.group(1).strip(" ,.!?")
            if content:
                arguments["message"] = content
    else:
        content_match = re.search(
            r"\b(?:remind\s+me|set(?:\s+(?:me|a))?\s+reminder|"
            r"create\s+a\s+reminder)\s+(?:to|about|that)\s+(.+?)\s*[?.!]*$",
            message,
            flags=re.IGNORECASE,
        )
        if content_match:
            content = content_match.group(1).strip(" ,.!?")
            if content:
                arguments["message"] = content
    return arguments


def _citation_arguments(message: str) -> dict[str, str]:
    topic = re.sub(
        r"^\s*(?:please\s+)?(?:(?:find|give\s+me|show\s+me|search\s+for)?\s*"
        r"(?:academic\s+)?(?:citations?|sources?|papers?|research)"
        r"|cite(?:\s+something)?)\s*(?:for|about|on)?\s*",
        "",
        message,
        flags=re.IGNORECASE,
    ).strip(" .?!")
    return {"topic": topic} if topic and topic.casefold() != message.strip(" .?!").casefold() else {}


def _schedule_arguments(message: str) -> dict[str, dict[str, list[str]]]:
    phrases = find_all_time_phrases(message)
    return {"availability_by_sender": {"requester": phrases}} if phrases else {}


def extract_arguments(intent: str, message: str) -> ExtractedToolCall:
    if intent not in TOOL_REGISTRY:
        raise ValueError(f"Unsupported tool intent: {intent}")
    extractors = {
        "book_meeting": _meeting_arguments,
        "web_search": _search_arguments,
        "set_reminder": extract_reminder_args,
        "find_citations": _citation_arguments,
        "match_schedule": _schedule_arguments,
    }
    arguments = extractors[intent](message)
    required = TOOL_REGISTRY[intent]["required_arguments"]
    missing = [name for name in required if not arguments.get(name)]
    return ExtractedToolCall(
        name=TOOL_REGISTRY[intent]["name"],
        arguments=arguments,
        missing_arguments=missing,
    )
