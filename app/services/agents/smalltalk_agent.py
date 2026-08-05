from app.services.agents.base_agent import BaseAgent
from app.services.generator import intent_response


class SmalltalkAgent(BaseAgent):
    name = "smalltalk"

    def __init__(self, intent: str):
        self.intent = intent

    def handle(self, message: str, history: list[dict[str, str]]) -> str:
        del message, history
        return intent_response(self.intent)

    @staticmethod
    def confirm_tool(tool_name: str, arguments: dict) -> str:
        if tool_name == "book_meeting":
            topic = arguments.get("topic", "the requested topic")
            when = arguments.get("time_reference", "the requested time")
            return f"I prepared a meeting request about {topic} for {when}."
        if tool_name == "web_search":
            query = arguments.get("query", "your request")
            return f"I prepared a web search for '{query}'."
        if tool_name == "set_reminder":
            message = arguments.get("message", "that")
            when = arguments.get("time", "the requested time")
            return f"I prepared a reminder to {message} for {when}."
        if tool_name == "find_citations":
            return f"I prepared an academic citation search for '{arguments.get('topic', '')}'."
        if tool_name == "match_schedule":
            return "I extracted the available time options for schedule matching."
        return "I prepared the requested action."
