"""Session-management API request and response models."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class SessionResetRequest(BaseModel):
    """Request body for clearing server-side chat session memory."""

    session_id: Optional[str] = Field(
        default=None,
        max_length=512,
        description="Signed session token returned by the chat endpoint.",
    )


class SessionResetResponse(BaseModel):
    """Result of a session reset operation."""

    status: Literal["ok"] = "ok"
    reset_count: int = Field(
        ...,
        ge=0,
        description="Number of in-memory sessions cleared.",
    )
