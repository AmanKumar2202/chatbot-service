import hashlib
import math
import threading
import time
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import settings
from app.core.metrics import CHROMA_LATENCY
from app.services.rag.embedder import get_embedder


class DocumentQuotaExceeded(ValueError):
    pass


@dataclass(frozen=True)
class RetrievedChunk:
    doc_id: str
    filename: str
    excerpt: str
    score: float


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")
    words = text.split()
    if not words:
        return []
    step = chunk_size - overlap
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += step
    return chunks


class InMemoryDocumentStore:
    """Process-local vector store for tests; production defaults to persistent Chroma."""

    def __init__(self):
        self._chunks: dict[str, list[tuple[str, str, str, list[float]]]] = {}
        self._lock = threading.RLock()

    def add_document(self, user_id: str, doc_id: str, filename: str, text: str) -> int:
        chunks = chunk_text(text, settings.rag_chunk_size, settings.rag_chunk_overlap)
        with self._lock:
            rows = self._chunks.get(user_id, [])
            existing = [row for row in rows if row[0] != doc_id]
            document_ids = {row[0] for row in existing}
            _enforce_quotas(document_ids, len(existing), doc_id, len(chunks))
        vectors = get_embedder().embed(chunks)
        with self._lock:
            existing = [row for row in self._chunks.get(user_id, []) if row[0] != doc_id]
            existing.extend(
                (doc_id, filename, chunk, vector)
                for chunk, vector in zip(chunks, vectors, strict=True)
            )
            self._chunks[user_id] = existing
        return len(chunks)

    def delete_document(self, user_id: str, doc_id: str) -> None:
        with self._lock:
            self._chunks[user_id] = [
                row for row in self._chunks.get(user_id, []) if row[0] != doc_id
            ]

    def retrieve(self, user_id: str, query: str, top_k: int) -> list[RetrievedChunk]:
        query_vector = get_embedder().embed([query])[0]
        query_norm = math.sqrt(sum(value * value for value in query_vector)) or 1.0
        ranked = []
        with self._lock:
            rows = list(self._chunks.get(user_id, []))
        for doc_id, filename, excerpt, vector in rows:
            vector_norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            score = sum(a * b for a, b in zip(query_vector, vector)) / (
                query_norm * vector_norm
            )
            ranked.append(RetrievedChunk(doc_id, filename, excerpt, float(score)))
        return sorted(ranked, key=lambda item: item.score, reverse=True)[:top_k]

    def is_ready(self) -> bool:
        return True


def _enforce_quotas(
    existing_document_ids: set[str],
    existing_chunk_count: int,
    doc_id: str,
    new_chunk_count: int,
) -> None:
    document_count = len(existing_document_ids | {doc_id})
    if document_count > settings.rag_max_documents_per_user:
        raise DocumentQuotaExceeded("Per-user document quota exceeded")
    if existing_chunk_count + new_chunk_count > settings.rag_max_chunks_per_user:
        raise DocumentQuotaExceeded("Per-user chunk quota exceeded")


class ChromaDocumentStore:
    """Shared Chroma HTTP store with one collection per hashed user identity."""

    def __init__(self):
        import chromadb
        self.client = chromadb.HttpClient(
            host=settings.rag_chroma_host,
            port=settings.rag_chroma_port,
            ssl=settings.rag_chroma_ssl,
            tenant=settings.rag_chroma_tenant,
            database=settings.rag_chroma_database,
        )

    @lru_cache(maxsize=256)
    def _collection(self, user_id: str):
        digest = hashlib.sha256(user_id.encode()).hexdigest()
        return self.client.get_or_create_collection(
            name=f"user_{digest}", metadata={"hnsw:space": "cosine"}
        )

    def add_document(self, user_id: str, doc_id: str, filename: str, text: str) -> int:
        started = time.perf_counter()
        try:
            return self._add_document(user_id, doc_id, filename, text)
        finally:
            CHROMA_LATENCY.labels("upsert").observe(time.perf_counter() - started)

    def _add_document(self, user_id: str, doc_id: str, filename: str, text: str) -> int:
        chunks = chunk_text(text, settings.rag_chunk_size, settings.rag_chunk_overlap)
        collection = self._collection(user_id)
        current = collection.get(include=["metadatas"])
        metadatas = current.get("metadatas") or []
        retained = [
            metadata for metadata in metadatas if str(metadata.get("doc_id")) != doc_id
        ]
        document_ids = {str(metadata.get("doc_id")) for metadata in retained}
        _enforce_quotas(document_ids, len(retained), doc_id, len(chunks))
        collection.delete(where={"doc_id": doc_id})
        if chunks:
            collection.upsert(
                ids=[f"{doc_id}:{index}" for index in range(len(chunks))],
                documents=chunks,
                embeddings=get_embedder().embed(chunks),
                metadatas=[
                    {"doc_id": doc_id, "filename": filename, "chunk_index": index}
                    for index in range(len(chunks))
                ],
            )
        return len(chunks)

    def delete_document(self, user_id: str, doc_id: str) -> None:
        started = time.perf_counter()
        try:
            self._collection(user_id).delete(where={"doc_id": doc_id})
        finally:
            CHROMA_LATENCY.labels("delete").observe(time.perf_counter() - started)

    def retrieve(self, user_id: str, query: str, top_k: int) -> list[RetrievedChunk]:
        started = time.perf_counter()
        try:
            return self._retrieve(user_id, query, top_k)
        finally:
            CHROMA_LATENCY.labels("query").observe(time.perf_counter() - started)

    def _retrieve(self, user_id: str, query: str, top_k: int) -> list[RetrievedChunk]:
        collection = self._collection(user_id)
        if collection.count() == 0:
            return []
        result = collection.query(
            query_embeddings=get_embedder().embed([query]),
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [
            RetrievedChunk(
                doc_id=str(metadata["doc_id"]),
                filename=str(metadata["filename"]),
                excerpt=document,
                score=max(0.0, 1.0 - float(distance)),
            )
            for document, metadata, distance in zip(
                documents, metadatas, distances, strict=True
            )
        ]

    def is_ready(self) -> bool:
        self.client.heartbeat()
        return True


@lru_cache
def get_document_store():
    if settings.rag_vector_backend == "memory":
        return InMemoryDocumentStore()
    if settings.rag_vector_backend != "chroma":
        raise ValueError(f"Unsupported RAG_VECTOR_BACKEND: {settings.rag_vector_backend}")
    return ChromaDocumentStore()
