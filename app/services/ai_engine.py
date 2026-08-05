from dataclasses import dataclass
import json
from typing import Any

from app.core.config import settings
from app.ml.predictor import predict_intent
from app.services.agents import (
    CodingHelpAgent,
    FormalWriterAgent,
    GeneralQAAgent,
    SmalltalkAgent,
)
from app.services.generator import intent_response
from app.services.tools import TOOL_REGISTRY, extract_arguments


GENERAL_AGENT = GeneralQAAgent()
FORMAL_AGENT = FormalWriterAgent()
CODING_AGENT = CodingHelpAgent()
SMALLTALK_AGENTS = {
    intent: SmalltalkAgent(intent) for intent in ("greeting", "help", "error", "bye")
}

AGENT_REGISTRY = {
    "paragraph": GENERAL_AGENT,
    "formal": FORMAL_AGENT,
    "code_help": CODING_AGENT,
    **SMALLTALK_AGENTS,
}

AGENT_OVERRIDES = {
    "general_qa": (GENERAL_AGENT, "paragraph"),
    "coding_help": (CODING_AGENT, "code_help"),
    "formal_writer": (FORMAL_AGENT, "formal"),
    "smalltalk": (SMALLTALK_AGENTS["help"], "help"),
}

FOLLOW_UP_PHRASES = {
    "another one",
    "tell me more",
    "more please",
    "continue",
    "go on",
    "what else",
}


def needs_history(message: str, agent_override: str | None = None) -> bool:
    normalized = message.casefold().strip(" .?!")
    if normalized in FOLLOW_UP_PHRASES:
        return True
    if agent_override == "general_qa":
        return True
    return any(
        marker in normalized
        for marker in ("paragraph", "tell me", "explain", "describe", "discuss")
    ) and not any(preposition in normalized for preposition in (" about ", " on ", " regarding "))


@dataclass(frozen=True)
class GeneratedReply:
    text: str
    intent: str
    confidence: float
    agent: str
    tool_call: dict[str, Any] | None = None


TOOL_RESULT_ACKNOWLEDGEMENTS = {
    "thanks",
    "thank you",
    "great",
    "okay",
    "ok",
    "done",
    "what happened",
    "did it work",
}


def _tool_result_reply(
    message: str, history: list[dict[str, str]]
) -> GeneratedReply | None:
    if not history or history[-1].get("role") != "tool":
        return None
    result = history[-1].get("content", "").strip()
    try:
        payload = json.loads(result)
    except (json.JSONDecodeError, TypeError):
        payload = None
    if isinstance(payload, dict) and payload.get("status") == "scheduled":
        remind_at = payload.get("remind_at") or payload.get("remindAt")
        text = (
            f"Your reminder is scheduled for {remind_at}."
            if remind_at
            else "Your reminder has been scheduled."
        )
        return GeneratedReply(text, "tool_result", 1.0, "tool_router")
    normalized = message.casefold().strip(" .?!")
    explicit_confirmation_request = normalized.startswith("present the tool result")
    if normalized not in TOOL_RESULT_ACKNOWLEDGEMENTS and not explicit_confirmation_request:
        return None
    status = payload.get("status") if isinstance(payload, dict) else None
    failed = status in {"unsupported", "unavailable", "unparseable_time", "not_connected", "failed", "error"}
    text = (
        f"The requested action did not complete successfully. Result: {result}"
        if failed
        else (f"The requested action completed. Result: {result}" if result else "The requested action completed.")
    )
    return GeneratedReply(text, "tool_result", 1.0, "tool_router")


def _tool_reply(intent: str, message: str, confidence: float) -> GeneratedReply:
    extracted = extract_arguments(intent, message)
    tool_call = {
        "name": extracted.name,
        "arguments": extracted.arguments,
        "missing_arguments": extracted.missing_arguments,
    }
    if extracted.missing_arguments:
        missing = ", ".join(extracted.missing_arguments)
        text = f"I can prepare that action, but I still need: {missing}."
    elif extracted.name == "set_reminder":
        text = "Got it — I'll remind you about that."
    else:
        text = f"I'll help with that — {SmalltalkAgent.confirm_tool(extracted.name, extracted.arguments)}"
    return GeneratedReply(text, intent, confidence, "tool_router", tool_call)


def generate_reply(
    message: str,
    history: list[dict[str, str]],
    agent_override: str | None = None,
) -> GeneratedReply:
    tool_result = _tool_result_reply(message, history)
    if tool_result:
        return tool_result

    if agent_override in AGENT_OVERRIDES:
        agent, intent = AGENT_OVERRIDES[agent_override]
        return GeneratedReply(agent.handle(message, history), intent, 1.0, agent.name)

    normalized = message.casefold().strip(" .?!")
    if normalized in FOLLOW_UP_PHRASES:
        text = GENERAL_AGENT.handle(message, history)
        return GeneratedReply(text, "paragraph", 1.0, GENERAL_AGENT.name)

    prediction = predict_intent(message)
    if prediction.confidence < settings.confidence_threshold:
        return GeneratedReply(
            intent_response("clarify"),
            "clarify",
            prediction.confidence,
            GENERAL_AGENT.name,
        )

    if prediction.intent in TOOL_REGISTRY:
        return _tool_reply(prediction.intent, message, prediction.confidence)

    agent = AGENT_REGISTRY.get(prediction.intent, GENERAL_AGENT)
    return GeneratedReply(
        agent.handle(message, history),
        prediction.intent,
        prediction.confidence,
        agent.name,
    )
