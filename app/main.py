from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import APP_NAME, VERSION
from app.ml.model_loader import load_model
from app.models.schemas import CapabilityResponse
from app.routes import chatbot


@asynccontextmanager
async def lifespan(_app: FastAPI):
    load_model()
    yield


app = FastAPI(title=APP_NAME, version=VERSION, lifespan=lifespan, docs_url="/docs", redoc_url=None)
app.include_router(chatbot.router, prefix="/api/v1", tags=["AI"])
app.include_router(chatbot.router, prefix="/api/chatbot", tags=["Legacy"])


@app.get("/health")
def health():
    return {"status": "ok", "service": APP_NAME, "version": VERSION}


@app.get("/api/v1/capabilities", response_model=CapabilityResponse)
def capabilities():
    return CapabilityResponse()
