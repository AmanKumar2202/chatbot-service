import json
import random
import re
from pathlib import Path


KNOWLEDGE_PATH = Path(__file__).resolve().parents[1] / "data" / "knowledge_base.json"
KNOWLEDGE_BASE: dict[str, list[str]] = json.loads(KNOWLEDGE_PATH.read_text(encoding="utf-8"))

INTENT_RESPONSES = {
    "greeting": [
        "Hello! What would you like help with today?",
        "Hi there. I can draft a paragraph or a formal message for you.",
        "Welcome! Tell me what you would like to write.",
        "Hey! How can I help?",
        "Good to hear from you. What shall we work on?",
    ],
    "help": [
        "I can generate a topic-based paragraph or draft a formal message. Try: 'write a paragraph about cybersecurity'.",
        "Ask me for a paragraph on a topic, or a formal message to someone about a specific request.",
        "I help with short informative paragraphs and professional messages. Tell me the topic or recipient and purpose.",
        "Try 'tell me about renewable energy' or 'write a formal message to HR regarding leave'.",
        "Describe what you want written and include the topic or the message recipient and reason.",
    ],
    "error": [
        "That seems to describe a problem. Please share what you tried and what went wrong.",
        "I can help clarify the issue. What result did you expect, and what happened instead?",
        "Please provide the error wording or a little more context so I can respond accurately.",
        "Something sounds off. Could you describe the problem in one or two sentences?",
        "Let's narrow it down: what action led to the error?",
    ],
    "bye": [
        "Goodbye! Come back whenever you need help writing.",
        "See you later!",
        "Take care, and have a great day.",
        "Thanks for chatting. Goodbye!",
        "Until next time!",
    ],
    "clarify": [
        "I'm not sure I understood. Could you rephrase that?",
        "Could you add a little more detail so I can choose the right response?",
        "I may have misunderstood. Are you asking for a paragraph or a formal message?",
        "Please reword that request and include the topic or intended recipient.",
        "I need a bit more context before I can answer confidently.",
    ],
}


def intent_response(intent: str) -> str:
    return random.choice(INTENT_RESPONSES[intent])


def detect_topic_category(topic: str) -> str | None:
    normalized = topic.casefold()
    return next((key for key in KNOWLEDGE_BASE if key in normalized), None)


def extract_topic(message: str) -> str | None:
    patterns = [
        r"\b(?:on|about|regarding)\b\s+(.+?)(?:[?.!]|$)",
        r"\b(?:explain|describe|discuss)\b\s+(.+?)(?:[?.!]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, message.casefold())
        if match:
            return match.group(1).strip()
    return None


def generate_paragraph(topic: str) -> str:
    topic = topic.strip(" .?!")
    display_topic = topic[0].upper() + topic[1:] if topic else "This topic"
    introductions = [
        f"{display_topic} is an important subject with a growing influence on modern life.",
        f"Understanding {display_topic} helps explain several changes taking place today.",
        f"{display_topic} connects practical decisions with broader social and technical developments.",
        f"Interest in {display_topic} continues to grow across communities and industries.",
    ]
    bodies = [
        "Its development creates useful opportunities as well as questions that require careful judgment.",
        "The subject continues to evolve as research, experience, and public needs change.",
        "A balanced understanding considers its practical benefits, limitations, and long-term effects.",
        "Learning the core ideas makes it easier to evaluate new developments in this area.",
    ]
    conclusions = [
        f"Overall, {display_topic} will remain relevant as people adapt it to new challenges.",
        f"In conclusion, thoughtful use of knowledge about {display_topic} can support better decisions.",
        f"As the field develops, informed discussion of {display_topic} will become even more valuable.",
        f"For these reasons, {display_topic} deserves continued attention and careful study.",
    ]
    category = detect_topic_category(topic)
    facts = random.sample(KNOWLEDGE_BASE[category], 3) if category else []
    return " ".join(
        [random.choice(introductions), *facts, random.choice(bodies), random.choice(conclusions)]
    )


def extract_formal_details(message: str) -> tuple[str, str] | None:
    match = re.search(
        r"\bto\s+(?P<recipient>[\w.' -]+?)(?:\s+(?:for|regarding|about)\s+)(?P<action>.+?)(?:[?.!]|$)",
        message,
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    recipient = match.group("recipient").strip().title()
    action = match.group("action").strip()
    return recipient, action[0].lower() + action[1:] if action else action


def generate_formal_message(recipient: str, action: str) -> str:
    templates = [
        "Dear {recipient},\n\nI hope you are doing well. I am writing regarding {action}. "
        "I would appreciate your assistance with this matter.\n\nThank you.\nBest regards,",
        "Hello {recipient},\n\nI would like to contact you regarding {action}. Please let me "
        "know if you need any further information.\n\nSincerely,",
        "Dear {recipient},\n\nPlease accept this message as a formal request concerning {action}. "
        "Thank you for your time and consideration.\n\nKind regards,",
        "Dear {recipient},\n\nI am reaching out about {action}. I would be grateful if you could "
        "review this request at your convenience.\n\nWith thanks,",
    ]
    return random.choice(templates).format(recipient=recipient, action=action)


def formal_clarification() -> str:
    return (
        "Please include both the recipient and reason, for example: "
        "'write a formal message to my manager regarding annual leave'."
    )
