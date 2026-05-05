"""Session-id resolution for authenticated HTTP requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from uuid import uuid4

from core.config import get_settings
from core.session_tokens import (
    SessionTokenError,
    create_session_token,
    parse_session_token,
)

ANONYMOUS_OWNER_ID = "anonymous"


class SessionSigningSecretMissing(RuntimeError):
    """Raised when signed client session ids cannot be produced or checked."""


@dataclass(frozen=True)
class ResolvedClientSession:
    """A browser session token resolved to the internal SessionStore key."""

    store_session_id: str
    client_session_id: str
    owner_id: str


def session_owner_id(
    credentials: Optional[Any],
) -> str:
    """Return the owner id that client session tokens must be bound to."""
    if credentials and credentials.decoded:
        sub = credentials.decoded.get("sub")
        if isinstance(sub, str) and sub:
            return f"user:{sub}"
    return ANONYMOUS_OWNER_ID


def session_id_prefix(owner_id: str) -> str:
    """Return the internal SessionStore key prefix for an owner."""
    if owner_id == ANONYMOUS_OWNER_ID:
        return "anon:"
    return f"{owner_id}:"


def new_store_session_id(owner_id: str) -> str:
    """Create a fresh internal SessionStore key for this owner."""
    return f"{session_id_prefix(owner_id)}{uuid4().hex}"


def get_session_token_secret() -> str:
    """Return the configured secret used to sign client session tokens."""
    settings = get_settings()
    secret = settings.session_signing_secret.strip() or settings.openai_api_key.strip()
    if not secret:
        raise SessionSigningSecretMissing(
            "SESSION_SIGNING_SECRET or OPENAI_API_KEY is required for session tokens."
        )
    return secret


def sign_store_session_id(*, store_session_id: str, owner_id: str) -> str:
    """Return the client-safe signed session token for a store key."""
    return create_session_token(
        store_session_id=store_session_id,
        owner_id=owner_id,
        secret=get_session_token_secret(),
    )


def validate_client_session_id(*, client_session_id: str, owner_id: str) -> str:
    """Validate a browser-provided session token and return the store key."""
    store_session_id = parse_session_token(
        client_session_id,
        expected_owner_id=owner_id,
        secret=get_session_token_secret(),
    )
    if not store_session_id.startswith(session_id_prefix(owner_id)):
        raise SessionTokenError("Session token id does not match its owner.")
    return store_session_id


def resolve_client_session(
    *,
    client_session_id: Optional[str],
    credentials: Optional[Any],
) -> ResolvedClientSession:
    """Resolve an optional browser token into store and client session ids."""
    owner_id = session_owner_id(credentials)

    if client_session_id:
        store_session_id = validate_client_session_id(
            client_session_id=client_session_id,
            owner_id=owner_id,
        )
        return ResolvedClientSession(
            store_session_id=store_session_id,
            client_session_id=client_session_id,
            owner_id=owner_id,
        )

    store_session_id = new_store_session_id(owner_id)
    return ResolvedClientSession(
        store_session_id=store_session_id,
        client_session_id=sign_store_session_id(
            store_session_id=store_session_id,
            owner_id=owner_id,
        ),
        owner_id=owner_id,
    )
