from functools import lru_cache
import threading
import time
from typing import Protocol

from app.core.config import settings
from app.core.metrics import EMBEDDING_LATENCY


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    """Lazy, local sentence-transformer embedding adapter."""

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._lock = threading.RLock()

    @property
    def model(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from sentence_transformers import SentenceTransformer

                    self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        started = time.perf_counter()
        try:
            with self._lock:
                vectors = self.model.encode(
                    texts,
                    normalize_embeddings=True,
                    show_progress_bar=False,
                    batch_size=64,
                )
        finally:
            EMBEDDING_LATENCY.observe(time.perf_counter() - started)
        return vectors.tolist()


class HashingEmbedder:
    """Deterministic offline backend used for tests and constrained deployments."""

    def __init__(self):
        from sklearn.feature_extraction.text import HashingVectorizer

        self.vectorizer = HashingVectorizer(
            n_features=1_024,
            alternate_sign=False,
            norm="l2",
            ngram_range=(1, 2),
        )

    def embed(self, texts: list[str]) -> list[list[float]]:
        started = time.perf_counter()
        try:
            return self.vectorizer.transform(texts).toarray().tolist()
        finally:
            EMBEDDING_LATENCY.observe(time.perf_counter() - started)


@lru_cache
def get_embedder() -> Embedder:
    if settings.rag_embedding_backend == "hashing":
        return HashingEmbedder()
    if settings.rag_embedding_backend != "sentence_transformers":
        raise ValueError(
            f"Unsupported RAG_EMBEDDING_BACKEND: {settings.rag_embedding_backend}"
        )
    return SentenceTransformerEmbedder(settings.rag_embedding_model)
