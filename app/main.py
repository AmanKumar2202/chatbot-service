import logging
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import anyio.to_thread
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import settings
from app.core.logging import configure_json_logging
from app.core.metrics import RATE_LIMIT_REJECTIONS, THREADPOOL_BORROWED
from app.core.rate_limit import limiter
from app.core.request_context import RequestContextMiddleware
from app.ml.model_loader import load_model, model_is_loaded
from app.routes import chatbot
from app.services.rag.document_store import get_document_store
from app.services.rag.embedder import get_embedder


configure_json_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_model()
    if settings.service_role != "general" and settings.rag_warmup_on_startup:
        import torch

        torch.set_num_threads(settings.torch_num_threads)
        get_embedder().embed(["readiness warmup"])
    logger.info(
        "startup_validation_complete model_ready=true rag_warmed=%s",
        settings.rag_warmup_on_startup,
    )
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
app.state.limiter = limiter


async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    RATE_LIMIT_REJECTIONS.labels("http").inc()
    return _rate_limit_exceeded_handler(request, exc)


app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "X-Service-Key", "X-Request-Id", "X-User-Id"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    started_at = time.perf_counter()
    request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("unhandled_request_error request_id=%s", request_id)
        response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
    response.headers["X-Request-Id"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{(time.perf_counter() - started_at) * 1000:.2f}"
    thread_limiter = anyio.to_thread.current_default_thread_limiter()
    THREADPOOL_BORROWED.set(thread_limiter.borrowed_tokens)
    return response


app.add_middleware(
    RequestContextMiddleware,
    max_body_bytes=settings.max_request_body_bytes,
)
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["chatbot"])
Instrumentator().instrument(app).expose(app, include_in_schema=False)


@app.get("/health", tags=["health"])
def health():
    return {"status": "alive"}


@app.get("/ready", tags=["health"])
def ready():
    loaded = model_is_loaded()
    rag_ready = False
    if settings.service_role != "general":
        try:
            rag_ready = bool(get_document_store().is_ready())
        except Exception:
            logger.warning("rag_readiness_check_failed", exc_info=True)
    return JSONResponse(
        status_code=200 if loaded else 503,
        content={"ready": loaded, "rag_ready": rag_ready},
    )


STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
