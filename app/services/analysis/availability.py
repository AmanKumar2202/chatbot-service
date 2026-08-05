from collections import defaultdict
from typing import Any

from app.services.tools.argument_extractor import find_all_time_phrases


def extract_availability(
    messages: list[dict[str, Any]],
) -> dict[str, list[str]]:
    availability: defaultdict[str, list[str]] = defaultdict(list)
    for message in messages:
        sender = str(message["sender"])
        for phrase in find_all_time_phrases(str(message["content"])):
            if phrase not in availability[sender]:
                availability[sender].append(phrase)
    return dict(availability)
