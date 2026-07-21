"""Generate a balanced intent dataset for Whispr's supported assistant tasks."""
import json
from pathlib import Path

INTENTS = {
    "reply": [
        "write a short reply telling them {topic}", "generate a friendly and natural reply confirming {topic}",
        "draft a reply saying {topic}", "help me respond that {topic}", "reply politely that {topic}",
        "write a response to tell them {topic}", "create a casual reply about {topic}", "respond by saying {topic}",
        "make a concise reply that says {topic}", "write a warm response explaining {topic}",
    ],
    "formal": [
        "write a humanized formal email to my {person} about {topic}", "generate a formal message for {person} regarding {topic}",
        "draft a professional mail to {person} requesting {topic}", "compose a polite business email for {person} about {topic}",
        "write an official message to {person} concerning {topic}", "create a natural professional email to {person} for {topic}",
    ],
    "summarize": [
        "summarize this long text", "make this passage shorter", "give me a concise summary", "shorten this into three sentences",
        "extract the main points from this text", "summarise the following conversation", "provide a brief overview",
        "turn this long content into a short summary", "what are the key points in this passage", "condense this text",
    ],
    "paragraph": [
        "write a paragraph about {topic}", "explain {topic} in a paragraph", "generate informative content on {topic}",
        "create a short article about {topic}", "describe {topic} clearly", "write an overview of {topic}",
    ],
    "greeting": ["hello", "hi there", "hey assistant", "good morning", "good evening", "how are you", "nice to meet you"],
    "help": ["can you help me", "I need assistance", "what can you do", "help me write something", "I need some guidance", "show me your features"],
    "error": ["I have an error", "help me fix a bug", "my code is not working", "the application crashed", "I am facing an issue", "debug this problem"],
    "bye": ["goodbye", "see you later", "talk to you soon", "bye for now", "catch you later", "thanks bye"],
}

TOPICS = ["two days of leave", "a project delay", "dinner tomorrow evening", "being busy today but free this weekend", "document verification", "a meeting on Friday", "artificial intelligence", "software development", "remote work", "the environment"]
PEOPLE = ["manager", "HR manager", "team lead", "client", "professor", "colleague"]


def build():
    rows = []
    for label, patterns in INTENTS.items():
        for pattern in patterns:
            if "{person}" in pattern:
                for index, topic in enumerate(TOPICS):
                    rows.append({"text": pattern.format(person=PEOPLE[index % len(PEOPLE)], topic=topic), "label": label})
            elif "{topic}" in pattern:
                for topic in TOPICS:
                    rows.append({"text": pattern.format(topic=topic), "label": label})
            else:
                variants = [pattern, f"please {pattern}", f"{pattern} please", f"assistant, {pattern}", f"could you respond to: {pattern}", f"I want to say {pattern}", f"{pattern} right now", f"can we start with {pattern}"]
                rows.extend({"text": text, "label": label} for text in variants)
    # Deduplicate while retaining deterministic order.
    unique = list({(row["text"].lower(), row["label"]): row for row in rows}.values())
    Path(__file__).with_name("training_data.json").write_text(json.dumps(unique, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated {len(unique)} balanced task examples")


if __name__ == "__main__":
    build()
