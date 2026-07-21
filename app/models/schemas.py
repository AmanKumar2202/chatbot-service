from typing import Literal

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=5000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    user_id: str = Field(min_length=1, max_length=128)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class ChatResponse(BaseModel):
    reply: str
    intent: str
    confidence: float
    model: str = "whispr-intent-v1"


class SmartReplyRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    count: int = Field(default=3, ge=1, le=5)


class SmartReplyResponse(BaseModel):
    replies: list[str]
    intent: str


class CapabilityResponse(BaseModel):
    chat: bool = True
    smart_replies: bool = True
    translation: bool = False
    transcription: bool = False
    paragraph_generation: bool = True
    formal_message_generation: bool = True
