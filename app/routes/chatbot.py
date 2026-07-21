import secrets

from fastapi import APIRouter, Depends, Header, HTTPException

from app.core.config import SERVICE_API_KEY
from app.models.schemas import ChatRequest, ChatResponse, SmartReplyRequest, SmartReplyResponse
from app.services.ai_engine import generate_reply, generate_smart_replies

router = APIRouter()


def require_service_key(x_service_key: str | None = Header(default=None)) -> None:
    if SERVICE_API_KEY and (not x_service_key or not secrets.compare_digest(x_service_key, SERVICE_API_KEY)):
        raise HTTPException(status_code=401, detail="Invalid service credentials")


@router.post("/respond", response_model=ChatResponse, dependencies=[Depends(require_service_key)])
async def chatbot_response(request: ChatRequest):
    history = [turn.model_dump() for turn in request.history]
    reply, intent, confidence = generate_reply(request.message, history)
    return ChatResponse(reply=reply, intent=intent, confidence=confidence)


@router.post("/smart-replies", response_model=SmartReplyResponse, dependencies=[Depends(require_service_key)])
async def smart_replies(request: SmartReplyRequest):
    replies, intent = generate_smart_replies(request.message, request.count)
    return SmartReplyResponse(replies=replies, intent=intent)
