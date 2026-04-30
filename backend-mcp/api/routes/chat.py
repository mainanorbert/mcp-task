"""Chat HTTP routes: validate input, delegate to service, map responses."""

from fastapi import APIRouter, Depends, HTTPException, Request
from openai import AsyncOpenAI

from api.deps import get_openai_client
from core.config import get_settings
from core.logging import get_logger
from core.prompts import get_chat_system_prompt
from schemas.chat import ChatRequest, ChatResponse
from services.chat_service import ChatCompletionError, complete_chat

router = APIRouter()
logger = get_logger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    body: ChatRequest,
    request: Request,
    openai_client: AsyncOpenAI = Depends(get_openai_client),
) -> ChatResponse:
    """Accept a chat turn and return the assistant reply."""
    if body.messages[-1].role != "user":
        raise HTTPException(
            status_code=400,
            detail="The last message must be from the user.",
        )

    settings = get_settings()
    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        "chat_request_started request_id=%s model=%s message_count=%s",
        request_id,
        settings.openai_model,
        len(body.messages),
    )

    history = [{"role": m.role, "content": m.content} for m in body.messages]
    try:
        message = await complete_chat(
            client=openai_client,
            model=settings.openai_model,
            system_prompt=get_chat_system_prompt(),
            conversation=history,
        )
    except ChatCompletionError as exc:
        logger.warning("chat_request_failed request_id=%s error=%s", request_id, exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logger.info("chat_request_completed request_id=%s", request_id)
    return ChatResponse(message=message)
