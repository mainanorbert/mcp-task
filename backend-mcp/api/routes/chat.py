"""Chat HTTP routes: validate input, delegate to service, map responses.

The endpoint is deliberately thin: it does the minimal request shaping and
hands off to :func:`services.chat_service.handle_chat_turn`, which owns all
business logic (memory + agent + MCP tools).
"""

from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_clerk_auth import HTTPAuthorizationCredentials  # type: ignore

from api.deps import get_session_store, maybe_clerk_auth
from core.config import get_settings
from core.logging import get_logger
from core.prompts import get_meridian_system_prompt
from schemas.chat import ChatRequest, ChatResponse
from services.chat_service import ChatServiceError, handle_chat_turn
from services.session_store import SessionStore

router = APIRouter()
logger = get_logger(__name__)


def _resolve_session_id(
    body_session_id: Optional[str],
    credentials: Optional[HTTPAuthorizationCredentials],
) -> str:
    """Pick the session id from (priority): explicit body, Clerk user id, fresh uuid."""
    if body_session_id:
        return body_session_id
    if credentials and credentials.decoded:
        sub = credentials.decoded.get("sub")
        if isinstance(sub, str) and sub:
            return f"user:{sub}"
    return f"anon:{uuid4().hex}"


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    body: ChatRequest,
    request: Request,
    clerk_credentials: Optional[HTTPAuthorizationCredentials] = Depends(maybe_clerk_auth),
    session_store: SessionStore = Depends(get_session_store),
) -> ChatResponse:
    """Accept one chat turn and return the agent's reply."""
    if body.messages[-1].role != "user":
        raise HTTPException(
            status_code=400,
            detail="The last message must be from the user.",
        )

    settings = get_settings()
    request_id = getattr(request.state, "request_id", "unknown")
    user_id = (
        (clerk_credentials.decoded or {}).get("sub", "unknown")
        if clerk_credentials
        else "anonymous"
    )
    session_id = _resolve_session_id(body.session_id, clerk_credentials)
    user_message = body.messages[-1].content

    logger.info(
        "chat_request_started request_id=%s user_id=%s session_id=%s model=%s mcp=%s msg_len=%d",
        request_id,
        user_id,
        session_id,
        settings.openai_model,
        settings.mcp_server_url,
        len(user_message),
    )

    try:
        reply = await handle_chat_turn(
            session_store=session_store,
            session_id=session_id,
            user_message=user_message,
            model=settings.openai_model,
            instructions=get_meridian_system_prompt(),
            mcp_server_url=settings.mcp_server_url,
            mcp_timeout_seconds=settings.mcp_request_timeout_seconds,
            max_turns=settings.agent_max_turns,
        )
    except ChatServiceError as exc:
        logger.warning(
            "chat_request_failed request_id=%s session_id=%s error=%s",
            request_id,
            session_id,
            exc,
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    logger.info(
        "chat_request_completed request_id=%s session_id=%s reply_len=%d",
        request_id,
        session_id,
        len(reply),
    )
    return ChatResponse(message=reply, session_id=session_id)
