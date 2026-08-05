from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings


class HistoryTurn(BaseModel):
    role: Literal["user", "assistant", "tool"]
    content: str

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("history content must not be empty")
        return value


class ChatRequest(BaseModel):
    message: str = Field(max_length=settings.max_message_length)
    user_id: str = Field(max_length=128)
    history: list[HistoryTurn] = Field(default_factory=list)
    agent_override: Literal["general_qa", "coding_help", "formal_writer", "smalltalk"] | None = None
    use_documents: bool = False

    @field_validator("message", "user_id")
    @classmethod
    def validate_nonempty(cls, value: str, info) -> str:
        value = value.strip()
        if not value:
            raise ValueError(f"{info.field_name} must not be empty or whitespace-only")
        return value

class SourceReference(BaseModel):
    doc_id: str
    filename: str
    excerpt: str


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    missing_arguments: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    reply: str
    intent: str
    confidence: float
    agent: str
    tool_call: ToolCall | None = None
    sources: list[SourceReference] = Field(default_factory=list)


class DocumentUploadRequest(BaseModel):
    doc_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._-]+$")
    filename: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, max_length=2_000_000)
    user_id: str = Field(min_length=1, max_length=128)

    @field_validator("filename", "text", "user_id")
    @classmethod
    def strip_nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be whitespace-only")
        return value


class DocumentUploadResponse(BaseModel):
    status: Literal["indexed"]
    doc_id: str
    chunks: int


class DocumentDeleteResponse(BaseModel):
    status: Literal["deleted"]
    doc_id: str


class SummarizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2_000_000)
    num_sentences: int = Field(default=5, ge=1, le=20)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be whitespace-only")
        return value


class SummarizeResponse(BaseModel):
    summary: str
    key_points: list[str]


class AnalysisMessage(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    sender: str = Field(min_length=1, max_length=128)
    content: str = Field(min_length=1, max_length=settings.max_message_length)

    @field_validator("id", "sender", "content")
    @classmethod
    def strip_analysis_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("analysis message fields must not be whitespace-only")
        return value


class AnalyzeRequest(BaseModel):
    mode: Literal["meeting_minutes", "action_items", "deadlines", "catch_up"]
    messages: list[AnalysisMessage] = Field(min_length=1, max_length=500)


class AnalyzeResponse(BaseModel):
    mode: str
    result: dict[str, Any]


class Flashcard(BaseModel):
    question: str
    answer: str


class FlashcardsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2_000_000)
    max_cards: int = Field(default=10, ge=1, le=50)

    @field_validator("text")
    @classmethod
    def validate_flashcard_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be whitespace-only")
        return value


class FlashcardsResponse(BaseModel):
    flashcards: list[Flashcard]


class HomeworkHelpRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=10_000)
    type: Literal["math", "essay"]

    @field_validator("prompt")
    @classmethod
    def validate_homework_prompt(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("prompt must not be whitespace-only")
        return value


class HomeworkHelpResponse(BaseModel):
    steps: list[str]
    final_answer: str | None
    is_generic_template: bool


class TranslateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=100_000)
    source_lang: str = Field(min_length=2, max_length=10, pattern=r"^[a-z-]+$")
    target_lang: str = Field(min_length=2, max_length=10, pattern=r"^[a-z-]+$")


class TranslateResponse(BaseModel):
    translated_text: str


class SupportedLanguage(BaseModel):
    code: str
    name: str


class SupportedLanguagesResponse(BaseModel):
    languages: list[SupportedLanguage]


class ScheduleParticipant(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=128)
    timezone: str = Field(default="UTC", min_length=1, max_length=64)


class ScheduleMatchRequest(BaseModel):
    messages: list[AnalysisMessage] = Field(min_length=1, max_length=500)
    participants: list[ScheduleParticipant] = Field(min_length=1, max_length=100)


class ParticipantAvailability(BaseModel):
    id: str
    name: str
    timezone: str
    windows: list[str]


class ScheduleMatchResponse(BaseModel):
    participants: list[ParticipantAvailability]


class ReceiptParseRequest(BaseModel):
    ocr_text: str = Field(min_length=1, max_length=100_000)

    @field_validator("ocr_text")
    @classmethod
    def validate_ocr_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("ocr_text must not be whitespace-only")
        return value


class ReceiptItem(BaseModel):
    name: str
    price: float


class ReceiptParseResponse(BaseModel):
    items: list[ReceiptItem]
    subtotal: float | None
    tax: float | None
    tip: float | None
    total: float | None
    parse_confidence: float = Field(ge=0, le=1)
