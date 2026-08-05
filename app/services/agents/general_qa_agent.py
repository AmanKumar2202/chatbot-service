from app.services.agents.base_agent import BaseAgent
from app.services.generator import detect_topic_category, extract_topic, generate_paragraph


class GeneralQAAgent(BaseAgent):
    name = "general_qa"

    @staticmethod
    def _previous_topic(history: list[dict[str, str]]) -> str | None:
        for turn in reversed(history):
            if turn.get("role") != "user":
                continue
            content = turn.get("content", "")
            topic = extract_topic(content) or detect_topic_category(content)
            if topic:
                return topic
        for turn in reversed(history):
            if turn.get("role") != "assistant":
                continue
            topic = detect_topic_category(turn.get("content", ""))
            if topic:
                return topic
        return None

    def handle(self, message: str, history: list[dict[str, str]]) -> str:
        topic = extract_topic(message) or self._previous_topic(history)
        if not topic:
            return "What topic would you like me to explain?"
        return generate_paragraph(topic)
