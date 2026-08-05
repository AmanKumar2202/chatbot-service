from app.services.agents.base_agent import BaseAgent
from app.services.generator import (
    extract_formal_details,
    formal_clarification,
    generate_formal_message,
)


class FormalWriterAgent(BaseAgent):
    name = "formal_writer"

    @staticmethod
    def _subject(action: str) -> str:
        cleaned = action.strip(" .?!")
        return f"Re: {cleaned.title()}" if cleaned else "Formal Request"

    def handle(
        self,
        message: str,
        history: list[dict[str, str]],
        mode: str = "chat",
    ) -> str | dict[str, str]:
        del history
        details = extract_formal_details(message)
        if not details:
            body = formal_clarification()
            return {"subject": "Additional Details Required", "body": body} if mode == "email" else body
        body = generate_formal_message(*details)
        if mode == "email":
            return {"subject": self._subject(details[1]), "body": body}
        return body
