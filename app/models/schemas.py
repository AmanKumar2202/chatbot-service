from pydantic import BaseModel
from typing import List


class ChatRequest(BaseModel):
    message: str
    user_id: str
    history: List[str] = []


class ChatResponse(BaseModel):
    reply: str