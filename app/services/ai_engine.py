from app.ml.predictor import predict_intent
from app.services.generator import (
    generate_paragraph,
    extract_topic,
    generate_formal_message,
    extract_formal_details
)

import random



DEFAULT_RESPONSES = [
    "I'm not sure I fully understand. Can you rephrase?",
    "Interesting… could you explain that a bit more?",
    "Got it, but I need a bit more clarity."
]



def generate_reply(message: str, history: list) -> str:
    try:
        intent = predict_intent(message)

        if intent == "paragraph":
            topic = extract_topic(message)
            return generate_paragraph(topic)

        elif intent == "formal":
            user, action = extract_formal_details(message)
            return generate_formal_message(user, action)

        return random.choice(DEFAULT_RESPONSES)

    except Exception as e:
        print("AI Engine Error:", str(e))
        return "⚠️ Something went wrong while processing your request."