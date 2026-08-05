import os


os.environ.setdefault("RAG_EMBEDDING_BACKEND", "hashing")
os.environ.setdefault("RAG_VECTOR_BACKEND", "memory")
os.environ.setdefault("RAG_SIMILARITY_THRESHOLD", "0.05")
os.environ.setdefault("RATE_LIMIT_STORAGE_URI", "memory://")

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers():
    return {"X-Service-Key": settings.service_api_key}
