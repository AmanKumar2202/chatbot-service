import re
from typing import Any

from app.services.analysis.deadlines import extract_deadline_phrase


ASSIGNMENT_CUES = [
    re.compile(
        r"^(?P<owner>@?[\w.-]+),?\s+(?:can you|could you|please)\s+(?P<task>.+)",
        re.IGNORECASE,
    ),
    re.compile(r"^(?P<owner>I)(?:'ll|\s+will)\s+(?P<task>.+)", re.IGNORECASE),
    re.compile(
        r"^(?P<owner>@?[\w.-]+)\s+(?:needs to|has to|should)\s+(?P<task>.+)",
        re.IGNORECASE,
    ),
]


def extract_action_items(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for message in messages:
        content = str(message["content"]).strip()
        for pattern in ASSIGNMENT_CUES:
            match = pattern.search(content)
            if not match:
                continue
            owner = match.group("owner")
            if owner.casefold() == "i":
                owner = str(message["sender"])
            task = match.group("task").strip(" .")
            items.append(
                {
                    "task": task,
                    "owner": owner,
                    "source_message_id": str(message["id"]),
                    "raw_deadline_phrase": extract_deadline_phrase(task),
                }
            )
            break
    return items
