from abc import ABC, abstractmethod


class BaseAgent(ABC):
    name: str

    @abstractmethod
    def handle(self, message: str, history: list[dict[str, str]]) -> str:
        """Return a deterministic response for this agent's domain."""
