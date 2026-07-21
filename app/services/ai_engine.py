import random
import re

from app.ml.predictor import predict_intent
from app.services.generator import extract_formal_details, extract_topic, generate_formal_message, generate_humanized_formal_message, generate_natural_reply, generate_paragraph, summarize_text

RESPONSES = {
    "greeting": ["Hey! How can I help you today?", "Hello! What would you like to work on?", "Hi there — what can I help with?"],
    "help": ["I can draft formal messages, generate paragraphs, or help you shape a response. What do you need?", "Tell me what you are trying to do and I will guide you."],
    "error": ["Share the error message and the relevant code or steps, and I will help narrow it down.", "What error are you seeing, and what did you expect to happen?"],
    "bye": ["Take care! Message me whenever you need help.", "See you later!"],
}

FALLBACKS = [
    "I can help with writing, formal messages, and common questions. Could you add a little more detail?",
    "I am not confident I understood that. Could you rephrase it with the outcome you want?",
]


def generate_reply(message: str, history: list | None = None) -> tuple[str, str, float]:
    lowered = message.lower().strip()
    if any(phrase in lowered for phrase in ("write a short reply", "generate a friendly", "draft a reply", "help me respond", "reply politely", "write a response", "generate a natural reply")):
        return generate_natural_reply(message), "reply", 1.0
    if any(phrase in lowered for phrase in ("summarize", "summary", "shorten this", "make this shorter")):
        content = message.split(":", 1)[1] if ":" in message else re.sub(r"^(summarize|summary|shorten this|make this shorter)\s*", "", message, flags=re.I)
        return summarize_text(content), "summarize", 1.0
    if any(phrase in lowered for phrase in ("humanized", "formal mail", "formal email", "formal message")):
        return generate_humanized_formal_message(message), "formal", 1.0
    intent, confidence = predict_intent(message)
    if confidence < 0.30:
        return random.choice(FALLBACKS), "unknown", confidence
    if intent == "paragraph":
        return generate_paragraph(extract_topic(message)), intent, confidence
    if intent == "formal":
        recipient, action = extract_formal_details(message)
        return generate_formal_message(recipient, action), intent, confidence
    if intent == "reply":
        return generate_natural_reply(message), intent, confidence
    return random.choice(RESPONSES.get(intent, FALLBACKS)), intent, confidence


def generate_smart_replies(message: str, count: int = 3) -> tuple[list[str], str]:
    intent, _ = predict_intent(message)
    lowered = message.lower()
    word_count = len(lowered.split())
    if any(word in lowered for word in ("project", "github", "code", "integration")) and any(word in lowered for word in ("update", "complete", "completed", "pending", "pushed", "review")):
        candidates = ["Thanks for the update. I'll review it shortly.", "Great progress — I'll check the latest changes.", "Noted. Please let me know when the review is complete."]
    elif any(phrase in lowered for phrase in ("can you send", "could you send", "please send", "please share", "can you share")):
        candidates = ["Sure, I'll send it shortly.", "Of course — I'll share it with you.", "I'll check and get back to you soon."]
    elif "?" in message and any(word in lowered for word in ("free", "available", "meet", "dinner", "call")):
        candidates = ["Yes, that works for me.", "Let me check and get back to you.", "I'm not available then. Can we choose another time?"]
    elif "?" in message:
        candidates = ["Yes, that sounds good.", "Let me check and get back to you.", "Could you share a little more detail?"]
    elif any(word in lowered for word in ("sorry", "apolog")):
        candidates = ["No worries at all.", "Thanks for letting me know.", "It's okay, I understand."]
    elif word_count <= 12 and any(word in lowered for word in ("thank", "thanks")):
        candidates = ["You're welcome!", "Happy to help.", "Anytime!"]
    elif intent == "formal":
        candidates = ["Thank you for the message. I'll review it.", "Noted with thanks. I'll get back to you shortly.", "I appreciate the update and will follow up soon."]
    else:
        candidates = {
        "greeting": ["Hey! How are you?", "Hi, good to hear from you!", "Hello! What’s up?"],
        "help": ["Of course, what do you need help with?", "Sure — send me the details.", "I’ll help however I can."],
        "error": ["Can you share the error message?", "What happened exactly?", "Let’s take a look together."],
        "bye": ["Talk to you later!", "Take care!", "See you soon."],
        "formal": ["I’ll review it and get back to you.", "Thank you for the update.", "Please share any additional details."],
        "paragraph": ["That’s interesting — tell me more.", "Thanks for sharing this.", "Could you explain that further?"],
        }.get(intent, ["Sounds good!", "Thanks for letting me know.", "Can you tell me more?"])
    return candidates[:count], intent
