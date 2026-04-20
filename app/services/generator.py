import random
import re

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