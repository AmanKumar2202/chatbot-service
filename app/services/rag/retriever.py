from app.core.config import settings
from app.services.rag.document_store import RetrievedChunk, get_document_store


def retrieve(user_id: str, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    candidates = get_document_store().retrieve(
        user_id=user_id,
        query=query,
        top_k=top_k or settings.rag_top_k,
    )
    return [
        chunk for chunk in candidates if chunk.score >= settings.rag_similarity_threshold
    ]
