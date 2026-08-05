import re

from sklearn.feature_extraction.text import TfidfVectorizer

from app.services.rag.summarizer import split_into_sentences


DEFINITION_PATTERNS = [
    re.compile(
        r"^(?P<term>.+?)\s+is\s+(?:defined\s+as|a|an|the)\s+(?P<definition>.+?)[.!?]?$",
        re.IGNORECASE,
    ),
    re.compile(r"^(?P<term>.+?)\s+means\s+(?P<definition>.+?)[.!?]?$", re.IGNORECASE),
    re.compile(
        r"^(?P<term>.+?)\s+refers\s+to\s+(?P<definition>.+?)[.!?]?$",
        re.IGNORECASE,
    ),
]


def _cloze_fallback(
    sentences: list[str], used_sentences: set[str], remaining: int
) -> list[dict[str, str]]:
    candidates = [sentence for sentence in sentences if sentence not in used_sentences]
    if not candidates or remaining <= 0:
        return []
    vectorizer = TfidfVectorizer(
        stop_words="english", ngram_range=(1, 2), max_features=500
    )
    try:
        matrix = vectorizer.fit_transform(candidates)
    except ValueError:
        return []
    terms = vectorizer.get_feature_names_out()
    cards: list[dict[str, str]] = []
    for row_index, sentence in enumerate(candidates):
        row = matrix.getrow(row_index)
        if row.nnz == 0:
            continue
        ranked = row.indices[row.data.argsort()[::-1]]
        term = next(
            (
                terms[index]
                for index in ranked
                if re.search(rf"\b{re.escape(terms[index])}\b", sentence, re.IGNORECASE)
            ),
            None,
        )
        if not term:
            continue
        question = re.sub(
            rf"\b{re.escape(term)}\b", "___", sentence, count=1, flags=re.IGNORECASE
        )
        cards.append({"question": question, "answer": term})
        if len(cards) >= remaining:
            break
    return cards


def generate_flashcards(text: str, max_cards: int = 10) -> list[dict[str, str]]:
    if max_cards < 1:
        raise ValueError("max_cards must be at least 1")
    sentences = split_into_sentences(text)
    cards: list[dict[str, str]] = []
    used_sentences: set[str] = set()
    for sentence in sentences:
        for pattern in DEFINITION_PATTERNS:
            match = pattern.search(sentence)
            if not match:
                continue
            term = match.group("term").strip()
            definition = match.group("definition").strip(" .")
            cards.append(
                {
                    "question": f"What is {term}?",
                    "answer": definition,
                }
            )
            used_sentences.add(sentence)
            break
        if len(cards) >= max_cards:
            return cards
    cards.extend(
        _cloze_fallback(sentences, used_sentences, max_cards - len(cards))
    )
    return cards[:max_cards]
