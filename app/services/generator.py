import random
import re
from collections import Counter

KNOWLEDGE_BASE = {
    "artificial intelligence": [
        "Artificial intelligence involves machine learning, deep learning, and neural networks.",
        "It is widely used in applications like chatbots, recommendation systems, and self-driving cars.",
        "AI helps automate tasks and improves decision-making using data.",
        "Companies use AI for data analysis, customer support, and predictive analytics."
    ],
    "cars": [
        "Cars are one of the most widely used modes of transportation in the world.",
        "Modern cars include advanced technologies such as electric engines and autonomous driving systems.",
        "They play a crucial role in daily commuting and logistics.",
        "The automobile industry continues to innovate with eco-friendly solutions like electric vehicles."
    ],
    "technology": [
        "Technology has transformed communication, education, and business operations.",
        "It includes fields like software development, artificial intelligence, and cloud computing.",
        "Modern technology enables automation and global connectivity.",
        "Innovations in technology continue to shape the future of society."
    ]
}

def detect_topic_category(topic: str):
    topic = topic.lower()

    for key in KNOWLEDGE_BASE:
        if key in topic:
            return key

    return None


def extract_topic(message: str):
    match = re.search(r"(on|about) (.+)", message.lower())
    return match.group(2) if match else "the topic"



def generate_paragraph(topic: str) -> str:
    topic_clean = topic.lower()
    topic_cap = topic.capitalize()

    intro = [
        f"{topic_cap} is an important subject that plays a significant role in modern life.",
        f"In today’s world, {topic_cap} has gained widespread importance.",
        f"{topic_cap} is a rapidly growing field influencing many industries."
    ]

    body_generic = [
        f"It has evolved significantly over time and continues to impact various aspects of society.",
        f"It contributes to innovation and development across multiple domains.",
        f"Understanding {topic_cap} helps individuals stay informed and make better decisions."
    ]

    conclusion = [
        f"In conclusion, {topic_cap} will continue to shape the future and remain highly relevant.",
        f"Overall, {topic_cap} is a crucial field with growing importance.",
        f"To sum up, {topic_cap} plays a vital role in modern development."
    ]

    # Inject knowledge
    category = detect_topic_category(topic_clean)
    knowledge_sentences = []

    if category:
        knowledge_sentences = random.sample(KNOWLEDGE_BASE[category], 2)

    paragraph = " ".join([
        random.choice(intro),
        *knowledge_sentences,  
        random.choice(body_generic),
        random.choice(body_generic),
        random.choice(conclusion)
    ])

    return paragraph


def extract_formal_details(message: str):
    user_match = re.search(r"to (\w+)", message.lower())
    action_match = re.search(r"to (.+)", message.lower())

    user = user_match.group(1) if user_match else "User"
    action = action_match.group(1) if action_match else "complete the task"

    return user.capitalize(), action


def generate_formal_message(user: str, action: str) -> str:
    templates = [
        f"Dear {user},\n\nI hope you are doing well. I would like to request you to {action}. Your assistance in this matter would be greatly appreciated.\n\nThank you.\nBest regards.",
        
        f"Hello {user},\n\nI hope this message finds you well. I am writing to kindly ask you to {action}. Please let me know if any additional information is needed.\n\nSincerely.",
        
        f"Dear {user},\n\nI would like to formally request you to {action}. I appreciate your time and support regarding this matter.\n\nKind regards."
    ]

    return random.choice(templates)


def generate_humanized_formal_message(message: str) -> str:
    recipient_match = re.search(r"(?:to|for)\s+([a-zA-Z][\w ]{0,30}?)(?:\s+(?:about|regarding|for|requesting|to)\s+|$)", message, re.I)
    recipient = recipient_match.group(1).strip() if recipient_match else "there"
    recipient = re.sub(r"^(my|the)\s+", "", recipient, flags=re.I).title()
    if recipient.lower() == "hr":
        recipient = "HR"
    topic_match = re.search(r"(?:about|regarding|requesting)\s+(.+)", message, re.I)
    if not topic_match:
        topic_match = re.search(r"\bfor\s+(.+)", message, re.I)
    topic = topic_match.group(1).strip(" .") if topic_match else "the matter we discussed"
    return f"Subject: Regarding {topic.title()}\n\nDear {recipient},\n\nI hope you're doing well. I wanted to reach out regarding {topic}. I would appreciate your consideration and would be happy to provide any additional details you may need.\n\nThank you for your time and understanding.\n\nBest regards"


def summarize_text(text: str, max_sentences: int = 3) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if len(sentences) <= max_sentences:
        return text
    words = re.findall(r"[a-zA-Z]{3,}", text.lower())
    stop = {"the", "and", "that", "this", "with", "from", "have", "for", "are", "was", "were", "but", "not", "you", "your", "into", "their", "they"}
    frequency = Counter(word for word in words if word not in stop)
    scored = []
    for index, sentence in enumerate(sentences):
        tokens = re.findall(r"[a-zA-Z]{3,}", sentence.lower())
        score = sum(frequency[token] for token in tokens) / max(len(tokens), 1)
        scored.append((score, index, sentence))
    selected = sorted(sorted(scored, reverse=True)[:max_sentences], key=lambda item: item[1])
    return " ".join(item[2] for item in selected)


def generate_natural_reply(message: str) -> str:
    patterns = [
        r"(?:telling them|saying|tell them|confirming(?: that)?|respond that|reply that)\s+(.+)",
        r"(?:response|reply)\s+(?:to\s+)?(?:say|saying)\s+(.+)",
    ]
    content = ""
    for pattern in patterns:
        match = re.search(pattern, message, re.I)
        if match:
            content = match.group(1).strip(" .")
            break
    if not content and "conversation:" in message.lower():
        content = message[message.lower().rfind("conversation:") + len("conversation:"):].split("Additional instruction:", 1)[0].strip().splitlines()[-1]
        return f"Thanks for letting me know. Regarding your message — {content[:180]}"
    if not content:
        return "What would you like the reply to communicate? Add the key detail and I’ll draft it naturally."
    if re.match(r"^(sounds?|tone|friendly|formal|confident|natural|short|concise|under\b|keep\b)", content, re.I):
        return "What should the reply say? Share the message or key point, and I’ll apply that tone."
    content = re.sub(r"\b[Ii] am\b", "I'm", content)
    content = re.sub(r"\b[Ii] will\b", "I'll", content)
    content = content[0].upper() + content[1:]
    if "available" in content.lower() and any(word in message.lower() for word in ("friendly", "natural", "warm")):
        return f"Sounds good! {content}."
    return f"{content}."
