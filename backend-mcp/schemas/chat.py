"""Chat API request and response body models."""

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    """One message from the client conversation history."""

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=32000)


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    messages: list[ChatMessageIn] = Field(
        ...,
        min_length=1,
        description="Prior turns; must end with a user message",
    )


class ChatResponse(BaseModel):
    """Assistant reply returned to the client."""

    message: str
