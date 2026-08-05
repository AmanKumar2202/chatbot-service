import re

import networkx as nx
from sklearn.metrics.pairwise import cosine_similarity

from app.services.rag.embedder import get_embedder


def split_into_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+(?=[^\s])", normalized)
        if sentence.strip()
    ]


def summarize(text: str, num_sentences: int = 5) -> dict[str, str | list[str]]:
    if num_sentences < 1:
        raise ValueError("num_sentences must be at least 1")
    sentences = split_into_sentences(text)
    if len(sentences) <= num_sentences:
        return {"summary": text, "key_points": sentences}

    embeddings = get_embedder().embed(sentences)
    similarity_matrix = cosine_similarity(embeddings)
    graph = nx.from_numpy_array(similarity_matrix)
    scores = nx.pagerank(graph)
    ranked = sorted(range(len(sentences)), key=lambda index: (-scores[index], index))
    top_indices = sorted(ranked[:num_sentences])
    summary_sentences = [sentences[index] for index in top_indices]
    return {
        "summary": " ".join(summary_sentences),
        "key_points": summary_sentences,
    }
