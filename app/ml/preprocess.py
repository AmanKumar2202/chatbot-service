import re

def clean_text(text: str) -> str:
    text = text.lower()  

    # remove special characters
    text = re.sub(r"[^a-zA-Z0-9\s]", "", text)

    # remove extra spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


def tokenize(text: str):
    return text.split()


def preprocess(text: str) -> str:
    text = clean_text(text)
    return text