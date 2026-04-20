from fastapi import APIRouter
from app.models.schemas import ChatRequest, ChatResponse
from app.services.ai_engine import generate_reply
from app.utils.memory import get_history, update_history

router = APIRouter()


@router.post("/respond", response_model=ChatResponse)
async def chatbot_response(request: ChatRequest):
    # Get previous messages
    history = get_history(request.user_id)

    # Generate reply
    reply = generate_reply(request.message, history)

    # Update memory
    update_history(request.user_id, request.message)

    return ChatResponse(reply=reply)
