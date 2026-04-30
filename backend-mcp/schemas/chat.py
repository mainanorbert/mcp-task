"""Chat API request and response body models."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    """One message from the client conversation history."""

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=32000)


class ChatRequest(BaseModel):
    """Request body for the chat endpoint.

    The full message history is still accepted for compatibility, but only the
    last user message is used per turn - the backend keeps server-side memory
    keyed by ``session_id``.
    """

    messages: list[ChatMessageIn] = Field(
        ...,
        min_length=1,
        description="Prior turns; must end with a user message",
    )
    session_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Stable id for the conversation. Defaults to the auth user id.",
    )


class ChatResponse(BaseModel):
    """Assistant reply returned to the client."""

    message: str
    session_id: str = Field(
        ...,
        description="Echo of the session id so the client can persist it.",
    )


class HealthResponse(BaseModel):
    """Simple readiness payload."""

    status: Literal["ok"] = "ok"
    service: str = "meridian-support-api"
    version: str = "0.2.0"
