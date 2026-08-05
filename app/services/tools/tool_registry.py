TOOL_REGISTRY = {
    "book_meeting": {
        "name": "book_meeting",
        "required_arguments": ["topic", "time_reference"],
        "description": "Ask the caller to create a calendar meeting.",
    },
    "web_search": {
        "name": "web_search",
        "required_arguments": ["query"],
        "description": "Ask the caller to perform a web search.",
    },
    "set_reminder": {
        "name": "set_reminder",
        "required_arguments": ["message", "time"],
        "description": "Ask the caller to schedule a reminder.",
    },
    "find_citations": {
        "name": "find_citations",
        "required_arguments": ["topic"],
        "description": "Ask the caller to search Semantic Scholar for academic sources.",
    },
    "match_schedule": {
        "name": "match_schedule",
        "required_arguments": ["availability_by_sender"],
        "description": "Ask the caller to resolve and intersect participant availability.",
    },
}
