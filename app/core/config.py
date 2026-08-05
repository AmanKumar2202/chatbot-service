from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Custom Chatbot"
    version: str = "3.0.0"
    service_role: Literal["all", "general", "rag"] = "all"
    service_api_key: str = Field(min_length=16)
    max_message_length: int = Field(default=5_000, gt=0)
    max_history_messages: int = Field(default=50, ge=2, le=500)
    rate_limit: str = "60/minute"
    rate_limit_storage_uri: str = "redis://localhost:6379/1"
    websocket_connection_rate_limit: str = "10/minute"
    websocket_message_rate_limit: str = "60/minute"
    websocket_idle_timeout_seconds: int = Field(default=60, ge=5, le=3600)
    max_request_body_bytes: int = Field(default=2_100_000, ge=1_024)
    server_limit_concurrency: int = Field(default=200, ge=1)
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:8000",
        "http://localhost:5173",
    ]
    confidence_threshold: float = Field(default=0.55, ge=0, le=1)
    rag_embedding_backend: str = "sentence_transformers"
    rag_vector_backend: str = "chroma"
    rag_embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rag_chroma_host: str = "localhost"
    rag_chroma_port: int = Field(default=8001, ge=1, le=65535)
    rag_chroma_ssl: bool = False
    rag_chroma_tenant: str = "default_tenant"
    rag_chroma_database: str = "default_database"
    rag_max_documents_per_user: int = Field(default=100, ge=1)
    rag_max_chunks_per_user: int = Field(default=5_000, ge=1)
    rag_warmup_on_startup: bool = False
    torch_num_threads: int = Field(default=1, ge=1, le=8)
    argos_data_directory: str = "./argos_data"
    rag_similarity_threshold: float = Field(default=0.5, ge=0, le=1)
    rag_top_k: int = Field(default=3, ge=1, le=10)
    rag_chunk_size: int = Field(default=500, ge=50, le=2_000)
    rag_chunk_overlap: int = Field(default=50, ge=0, le=500)
    stream_chunk_words: int = Field(default=8, ge=1, le=50)
    stream_delay_ms: int = Field(default=0, ge=0, le=1_000)
    stream_max_duration_seconds: float = Field(default=30.0, gt=0, le=600)

    @field_validator("rag_chunk_overlap")
    @classmethod
    def overlap_smaller_than_chunk(cls, value: int, info) -> int:
        chunk_size = info.data.get("rag_chunk_size", 500)
        if value >= chunk_size:
            raise ValueError("rag_chunk_overlap must be smaller than rag_chunk_size")
        return value

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
