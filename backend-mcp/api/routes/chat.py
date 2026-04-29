"""Chat HTTP routes: validate input, delegate to service, map responses."""

from fastapi import APIRouter, Depends, HTTPException
from openai import AsyncOpenAI

from api.deps import get_openai_client
from core.config import get_settings
from core.prompts import get_chat_system_prompt
from schemas.chat import ChatRequest, ChatResponse
from services.chat_service import ChatCompletionError, complete_chat
from services.web_research_service import (
    WebInvestigatorError,
    build_investigator_task,
    run_web_investigator,
)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    body: ChatRequest,
    openai_client: AsyncOpenAI = Depends(get_openai_client),
) -> ChatResponse:
    """Accept a chat turn, run completion via the service layer, return text."""
    if body.messages[-1].role != "user":
        raise HTTPException(
            status_code=400,
            detail="The last message must be from the user.",
        )

    settings = get_settings()

    if body.use_web_search:
        recent = [(m.role, m.content) for m in body.messages[-12:]]
        user_task = build_investigator_task(recent)
        try:
            text = await run_web_investigator(
                openai_client=openai_client,
                model_name=settings.openai_model,
                user_task=user_task,
                max_turns=settings.web_agent_max_turns,
                mcp_session_timeout_seconds=settings.mcp_playwright_session_timeout_seconds,
            )
        except WebInvestigatorError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        return ChatResponse(message=text)

    history = [{"role": m.role, "content": m.content} for m in body.messages]

    try:
        text = await complete_chat(
            client=openai_client,
            model=settings.openai_model,
            system_prompt=get_chat_system_prompt(),
            conversation=history,
        )
    except ChatCompletionError as exc:
        raise HTTPException(
            status_code=502,
            detail="Upstream model request failed.",
        ) from exc

    return ChatResponse(message=text)
