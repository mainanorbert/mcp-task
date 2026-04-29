"""Chat HTTP routes: validate input, delegate to service, map responses."""

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

from api.deps import get_openai_client
from core.config import get_settings
from core.logging import get_logger
from core.prompts import get_chat_system_prompt
from schemas.chat import ChatRequest
from services.chat_service import ChatCompletionError, stream_chat
from services.web_research_service import (
    WebInvestigatorError,
    build_investigator_task,
    run_web_investigator,
)

router = APIRouter()
logger = get_logger(__name__)


def sse_event(event: str, payload: dict[str, str] | None = None) -> str:
    """Format one server-sent event."""
    data = json.dumps(payload or {}, ensure_ascii=False)
    return f"event: {event}\ndata: {data}\n\n"


@router.post("/chat")
async def chat_endpoint(
    body: ChatRequest,
    request: Request,
    openai_client: AsyncOpenAI = Depends(get_openai_client),
) -> StreamingResponse:
    """Accept a chat turn and stream the assistant reply as server-sent events."""
    if body.messages[-1].role != "user":
        raise HTTPException(
            status_code=400,
            detail="The last message must be from the user.",
        )

    settings = get_settings()
    request_id = getattr(request.state, "request_id", "unknown")
    mode = "web_search" if body.use_web_search else "chat"
    logger.info(
        "chat_request_started request_id=%s mode=%s model=%s message_count=%s",
        request_id,
        mode,
        settings.openai_model,
        len(body.messages),
    )

    async def events() -> AsyncIterator[str]:
        try:
            if body.use_web_search:
                yield sse_event("status", {"message": "Searching the web..."})
                recent = [(m.role, m.content) for m in body.messages[-12:]]
                user_task = build_investigator_task(recent)
                text = await run_web_investigator(
                    openai_client=openai_client,
                    model_name=settings.openai_model,
                    user_task=user_task,
                    max_turns=settings.web_agent_max_turns,
                    mcp_session_timeout_seconds=settings.mcp_playwright_session_timeout_seconds,
                )
                if text:
                    yield sse_event("delta", {"content": text})
            else:
                history = [
                    {"role": m.role, "content": m.content} for m in body.messages
                ]
                async for delta in stream_chat(
                    client=openai_client,
                    model=settings.openai_model,
                    system_prompt=get_chat_system_prompt(),
                    conversation=history,
                ):
                    yield sse_event("delta", {"content": delta})
            logger.info(
                "chat_request_completed request_id=%s mode=%s",
                request_id,
                mode,
            )
            yield sse_event("done")
        except (ChatCompletionError, WebInvestigatorError) as exc:
            logger.warning(
                "chat_request_failed request_id=%s mode=%s error=%s",
                request_id,
                mode,
                exc,
            )
            yield sse_event("error", {"message": str(exc)})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
