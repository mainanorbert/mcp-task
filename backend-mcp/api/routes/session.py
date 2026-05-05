"""Session-management HTTP routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_clerk_auth import HTTPAuthorizationCredentials  # type: ignore

from api.deps import get_session_store, maybe_clerk_auth
from api.session_ids import (
    ANONYMOUS_OWNER_ID,
    SessionSigningSecretMissing,
    session_id_prefix,
    session_owner_id,
    validate_client_session_id,
)
from core.logging import get_logger
from core.session_tokens import SessionTokenError
from schemas.session import SessionResetRequest, SessionResetResponse
from services.session_store import SessionStore

router = APIRouter()
logger = get_logger(__name__)


@router.post("/session/reset", response_model=SessionResetResponse)
async def reset_session_endpoint(
    body: SessionResetRequest,
    request: Request,
    clerk_credentials: Optional[HTTPAuthorizationCredentials] = Depends(maybe_clerk_auth),
    session_store: SessionStore = Depends(get_session_store),
) -> SessionResetResponse:
    """Clear server-side chat memory for the current authenticated session."""
    owner_id = session_owner_id(clerk_credentials)

    try:
        if body.session_id:
            store_session_id = validate_client_session_id(
                client_session_id=body.session_id,
                owner_id=owner_id,
            )
            reset_count = 1 if await session_store.reset(store_session_id) else 0
        elif owner_id != ANONYMOUS_OWNER_ID:
            reset_count = await session_store.reset_by_prefix(session_id_prefix(owner_id))
        else:
            reset_count = 0
    except SessionTokenError as exc:
        raise HTTPException(
            status_code=403,
            detail="The provided session_id is invalid for this user.",
        ) from exc
    except SessionSigningSecretMissing as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info(
        "session_reset request_id=%s owner_id=%s reset_count=%d",
        getattr(request.state, "request_id", "unknown"),
        owner_id,
        reset_count,
    )
    return SessionResetResponse(reset_count=reset_count)
