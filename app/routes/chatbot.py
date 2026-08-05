import asyncio
import hashlib
import hmac
import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.core.auth import require_service_key
from app.core.config import settings
from app.core.rate_limit import allow_websocket, limiter, websocket_key
from app.ml.model_loader import ModelArtifactError
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    AnalyzeRequest,
    AnalyzeResponse,
    DocumentDeleteResponse,
    DocumentUploadRequest,
    DocumentUploadResponse,
    SourceReference,
    SummarizeRequest,
    SummarizeResponse,
    FlashcardsRequest,
    FlashcardsResponse,
    HomeworkHelpRequest,
    HomeworkHelpResponse,
    ReceiptParseRequest,
    ReceiptParseResponse,
    TranslateRequest,
    TranslateResponse,
    SupportedLanguagesResponse,
    ScheduleMatchRequest,
    ScheduleMatchResponse,
)
from app.services.analysis import (
    extract_availability,
    extract_action_items,
    extract_deadlines,
    generate_minutes,
)
from app.services.flashcards import generate_flashcards
from app.services.homework import help_with_essay, solve_math
from app.services.receipts import parse_receipt
from app.services.ai_engine import generate_reply
from app.services.rag.document_store import get_document_store
from app.services.rag.document_store import DocumentQuotaExceeded
from app.services.rag.retriever import retrieve
from app.services.rag.summarizer import summarize
from app.services.translation import UnsupportedLanguagePair, supported_languages, translate_text


logger = logging.getLogger(__name__)
router = APIRouter()


def _require_rag_role() -> None:
    if settings.service_role == "general":
        raise HTTPException(
            status_code=503,
            detail="RAG workload is disabled on this deployment",
        )


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    dependencies=[Depends(require_service_key)],
)
@limiter.limit(settings.rate_limit)
async def analyze_messages(
    request: Request, payload: AnalyzeRequest
) -> AnalyzeResponse:
    messages = [message.model_dump() for message in payload.messages]
    if payload.mode in {"meeting_minutes", "catch_up"}:
        _require_rag_role()
    if payload.mode == "meeting_minutes":
        result = await run_in_threadpool(generate_minutes, messages)
    elif payload.mode == "action_items":
        result = {"action_items": extract_action_items(messages)}
    elif payload.mode == "deadlines":
        result = {"deadlines": extract_deadlines(messages)}
    else:
        text = " ".join(message["content"] for message in messages)
        summary = await run_in_threadpool(summarize, text, 3)
        result = {
            "summary": summary["summary"],
            "bullet_points": summary["key_points"],
        }
    return AnalyzeResponse(mode=payload.mode, result=result)


@router.post(
    "/flashcards",
    response_model=FlashcardsResponse,
    dependencies=[Depends(require_service_key)],
)
@limiter.limit(settings.rate_limit)
async def make_flashcards(
    request: Request, payload: FlashcardsRequest
) -> FlashcardsResponse:
    cards = await run_in_threadpool(
        generate_flashcards, payload.text, payload.max_cards
    )
    return FlashcardsResponse(flashcards=cards)


@router.post(
    "/homework-help",
    response_model=HomeworkHelpResponse,
    dependencies=[Depends(require_service_key)],
)
@limiter.limit(settings.rate_limit)
async def homework_help(
    request: Request, payload: HomeworkHelpRequest
) -> HomeworkHelpResponse:
    try:
        helper = solve_math if payload.type == "math" else help_with_essay
        result = await run_in_threadpool(helper, payload.prompt)
    except (TypeError, ValueError, SyntaxError) as exc:
        raise HTTPException(
            status_code=422, detail=f"Unable to parse homework prompt: {exc}"
        ) from exc
    return HomeworkHelpResponse(**result)


@router.post(
    "/translate",
    response_model=TranslateResponse,
    dependencies=[Depends(require_service_key)],
)
@limiter.limit(settings.rate_limit)
async def translate(
    request: Request, payload: TranslateRequest
) -> TranslateResponse:
    _require_rag_role()
    try:
        translated = await run_in_threadpool(
            translate_text,
            payload.text,
            payload.source_lang,
            payload.target_lang,
        )
    except UnsupportedLanguagePair as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return TranslateResponse(translated_text=translated)


@router.get(
    "/translate/supported-languages",
    response_model=SupportedLanguagesResponse,
    dependencies=[Depends(require_service_key)],
)
@limiter.limit(settings.rate_limit)
async def list_supported_languages(request: Request) -> SupportedLanguagesResponse:
    languages = await run_in_threadpool(supported_languages)
    return SupportedLanguagesResponse(languages=languages)


@router.post(
    "/match-schedule",
    response_model=ScheduleMatchResponse,
    dependencies=[Depends(require_service_key)],
)
@limiter.limit(settings.rate_limit)
async def match_schedule(
    request: Request, payload: ScheduleMatchRequest
) -> ScheduleMatchResponse:
    messages = [message.model_dump() for message in payload.messages]
    availability = await run_in_threadpool(extract_availability, messages)
    participants = [
        {
            **participant.model_dump(),
            "windows": availability.get(participant.id, []),
        }
        for participant in payload.participants
    ]
    return ScheduleMatchResponse(participants=participants)


@router.post(
    "/receipt/parse",
    response_model=ReceiptParseResponse,
    dependencies=[Depends(require_service_key)],
)
@limiter.limit(settings.rate_limit)
async def parse_receipt_text(
    request: Request, payload: ReceiptParseRequest
) -> ReceiptParseResponse:
    result = await run_in_threadpool(parse_receipt, payload.ocr_text)
    return ReceiptParseResponse(**result)


@router.post(
    "/summarize",
    response_model=SummarizeResponse,
    dependencies=[Depends(require_service_key)],
)
@limiter.limit(settings.rate_limit)
async def summarize_document(
    request: Request, payload: SummarizeRequest
) -> SummarizeResponse:
    _require_rag_role()
    try:
        result = await run_in_threadpool(summarize, payload.text, payload.num_sentences)
    except Exception as exc:
        logger.exception("document_summarize_error request_id=%s", _request_id(request))
        raise HTTPException(status_code=500, detail="Unable to summarize document") from exc
    return SummarizeResponse(
        summary=result["summary"],
        key_points=result["key_points"],
    )


def _stream_chunks(text: str) -> list[str]:
    tokens = re.findall(r"\S+\s*", text)
    size = settings.stream_chunk_words
    return ["".join(tokens[index : index + size]) for index in range(0, len(tokens), size)]


def _respond(payload: ChatRequest) -> ChatResponse:
    if payload.use_documents:
        _require_rag_role()
    supplied_history = [turn.model_dump() for turn in payload.history]
    generated = generate_reply(
        payload.message, supplied_history, payload.agent_override
    )
    sources: list[SourceReference] = []
    reply = generated.text
    if payload.use_documents:
        chunks = retrieve(payload.user_id, payload.message)
        sources = [
            SourceReference(
                doc_id=chunk.doc_id,
                filename=chunk.filename,
                excerpt=chunk.excerpt,
            )
            for chunk in chunks
        ]
        if chunks:
            grounded = "\n\n".join(
                f"From '{chunk.filename}': {chunk.excerpt}" for chunk in chunks
            )
            reply = f"Based on your uploaded documents:\n\n{grounded}\n\n{reply}"
        else:
            reply = (
                "I couldn't find anything relevant in your uploaded documents for that "
                f"question.\n\n{reply}"
            )
    return ChatResponse(
        reply=reply,
        intent=generated.intent,
        confidence=generated.confidence,
        agent=generated.agent,
        tool_call=generated.tool_call,
        sources=sources,
    )


def _request_id(request: Request) -> str:
    return request.state.request_id


def _raise_pipeline_error(request: Request, exc: Exception) -> None:
    if isinstance(exc, HTTPException):
        raise exc
    request_id = _request_id(request)
    if isinstance(exc, ModelArtifactError):
        logger.error("model_artifact_error request_id=%s error=%s", request_id, exc)
        raise HTTPException(status_code=503, detail="Chat model is not ready") from exc
    logger.exception("chat_pipeline_error request_id=%s", request_id)
    raise HTTPException(status_code=500, detail="Unable to generate a response") from exc


@router.post(
    "/respond",
    response_model=ChatResponse,
    dependencies=[Depends(require_service_key)],
)
@limiter.limit(settings.rate_limit)
async def chatbot_response(request: Request, payload: ChatRequest) -> ChatResponse:
    try:
        response = await run_in_threadpool(_respond, payload)
    except Exception as exc:
        _raise_pipeline_error(request, exc)
    logger.info(
        "chat_response request_id=%s intent=%s confidence=%.3f",
        _request_id(request),
        response.intent,
        response.confidence,
    )
    return response


@router.post(
    "/stream",
    dependencies=[Depends(require_service_key)],
    response_class=StreamingResponse,
)
@limiter.limit(settings.rate_limit)
async def stream_response(request: Request, payload: ChatRequest) -> StreamingResponse:
    try:
        response = await run_in_threadpool(_respond, payload)
    except Exception as exc:
        _raise_pipeline_error(request, exc)

    async def event_stream():
        chunks = _stream_chunks(response.reply)
        stream_started = asyncio.get_running_loop().time()
        for index, chunk in enumerate(chunks):
            elapsed = asyncio.get_running_loop().time() - stream_started
            if elapsed >= settings.stream_max_duration_seconds:
                yield f"data: {json.dumps({'delta': ''.join(chunks[index:]), 'flushed': True})}\n\n"
                break
            yield f"data: {json.dumps({'delta': chunk})}\n\n"
            if settings.stream_delay_ms and index < len(chunks) - 1:
                await asyncio.sleep(settings.stream_delay_ms / 1_000)
        done = {
            "done": True,
            "intent": response.intent,
            "confidence": response.confidence,
            "agent": response.agent,
            "tool_call": response.tool_call.model_dump() if response.tool_call else None,
            "sources": [source.model_dump() for source in response.sources],
            "delivery_time_ms": round(
                (asyncio.get_running_loop().time() - stream_started) * 1_000, 2
            ),
        }
        yield f"data: {json.dumps(done)}\n\n"

    logger.info(
        "chat_stream request_id=%s intent=%s confidence=%.3f",
        _request_id(request),
        response.intent,
        response.confidence,
    )
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post(
    "/documents",
    response_model=DocumentUploadResponse,
    dependencies=[Depends(require_service_key)],
)
@limiter.limit(settings.rate_limit)
async def upload_document(
    request: Request, payload: DocumentUploadRequest
) -> DocumentUploadResponse:
    _require_rag_role()
    try:
        chunks = await run_in_threadpool(
            get_document_store().add_document,
            payload.user_id,
            payload.doc_id,
            payload.filename,
            payload.text,
        )
    except DocumentQuotaExceeded as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("document_index_error request_id=%s", _request_id(request))
        raise HTTPException(status_code=500, detail="Unable to index document") from exc
    logger.info(
        "document_indexed request_id=%s user_id_hash=%s doc_id=%s chunks=%d",
        _request_id(request),
        hashlib.sha256(payload.user_id.encode()).hexdigest()[:12],
        payload.doc_id,
        chunks,
    )
    return DocumentUploadResponse(status="indexed", doc_id=payload.doc_id, chunks=chunks)


@router.delete(
    "/documents/{doc_id}",
    response_model=DocumentDeleteResponse,
    dependencies=[Depends(require_service_key)],
)
@limiter.limit(settings.rate_limit)
async def remove_document(
    request: Request, doc_id: str, user_id: str
) -> DocumentDeleteResponse:
    _require_rag_role()
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,128}", doc_id):
        raise HTTPException(status_code=422, detail="Invalid document ID")
    if not user_id.strip():
        raise HTTPException(status_code=422, detail="user_id must not be empty")
    try:
        await run_in_threadpool(
            get_document_store().delete_document, user_id.strip(), doc_id
        )
    except Exception as exc:
        logger.exception("document_delete_error request_id=%s", _request_id(request))
        raise HTTPException(status_code=500, detail="Unable to delete document") from exc
    logger.info(
        "document_deleted request_id=%s user_id_hash=%s doc_id=%s",
        _request_id(request),
        hashlib.sha256(user_id.encode()).hexdigest()[:12],
        doc_id,
    )
    return DocumentDeleteResponse(status="deleted", doc_id=doc_id)


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    service_key = websocket.query_params.get("service_key", "")
    if not hmac.compare_digest(service_key, settings.service_api_key):
        await websocket.close(code=4401, reason="Invalid service key")
        return
    connection_user_id = websocket.query_params.get("user_id", "anonymous")
    connection_key = websocket_key(service_key, connection_user_id)
    if not allow_websocket(
        f"ws-connect:{connection_key}", settings.websocket_connection_rate_limit
    ):
        await websocket.close(code=4429, reason="Connection rate limit exceeded")
        return
    await websocket.accept()
    try:
        while True:
            try:
                incoming = await asyncio.wait_for(
                    websocket.receive_json(),
                    timeout=settings.websocket_idle_timeout_seconds,
                )
                payload = ChatRequest.model_validate(incoming)
                message_key = websocket_key(service_key, payload.user_id)
                if not allow_websocket(
                    f"ws-message:{message_key}", settings.websocket_message_rate_limit
                ):
                    await websocket.send_json({"error": "Message rate limit exceeded"})
                    await websocket.close(code=4429, reason="Message rate limit exceeded")
                    return
                response = await run_in_threadpool(_respond, payload)
                await websocket.send_json(response.model_dump())
            except asyncio.TimeoutError:
                await websocket.close(code=4408, reason="Idle timeout")
                return
            except ValueError as exc:
                await websocket.send_json({"error": str(exc)})
            except Exception:
                logger.exception("websocket_chat_pipeline_error")
                await websocket.send_json({"error": "Unable to generate a response"})
    except WebSocketDisconnect:
        logger.info("websocket_disconnected")
