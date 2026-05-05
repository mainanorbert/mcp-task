"""Signed client session-token helpers.

The browser never receives raw ``SessionStore`` keys. Instead, it receives a
compact HMAC-signed token that binds that store key to the authenticated owner.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

SESSION_TOKEN_VERSION = "v1"


class SessionTokenError(ValueError):
    """Raised when a client session token cannot be trusted."""


def _base64url_encode(raw: bytes) -> str:
    """Return unpadded URL-safe base64 text."""
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _base64url_decode(encoded: str) -> bytes:
    """Decode unpadded URL-safe base64 text."""
    padding = "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode((encoded + padding).encode("ascii"))


def _signature(signing_input: str, *, secret: str) -> str:
    """Return the HMAC signature for a token signing input."""
    digest = hmac.new(
        secret.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _base64url_encode(digest)


def create_session_token(
    *,
    store_session_id: str,
    owner_id: str,
    secret: str,
) -> str:
    """Create a signed token for ``store_session_id`` bound to ``owner_id``."""
    if not secret:
        raise SessionTokenError("Session token signing secret is empty.")

    payload = {
        "iat": int(time.time()),
        "owner": owner_id,
        "sid": store_session_id,
    }
    payload_segment = _base64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{SESSION_TOKEN_VERSION}.{payload_segment}"
    return f"{signing_input}.{_signature(signing_input, secret=secret)}"


def parse_session_token(
    token: str,
    *,
    expected_owner_id: str,
    secret: str,
) -> str:
    """Validate ``token`` and return the trusted store session id.

    Raises:
        SessionTokenError: If the token is malformed, forged, or owned by a
            different authenticated user.
    """
    if not secret:
        raise SessionTokenError("Session token signing secret is empty.")

    try:
        version, payload_segment, signature_segment = token.split(".", 2)
    except ValueError as exc:
        raise SessionTokenError("Malformed session token.") from exc

    if version != SESSION_TOKEN_VERSION:
        raise SessionTokenError("Unsupported session token version.")

    signing_input = f"{version}.{payload_segment}"
    expected_signature = _signature(signing_input, secret=secret)
    if not hmac.compare_digest(signature_segment, expected_signature):
        raise SessionTokenError("Session token signature is invalid.")

    try:
        payload: Any = json.loads(_base64url_decode(payload_segment))
    except (ValueError, json.JSONDecodeError) as exc:
        raise SessionTokenError("Session token payload is invalid.") from exc

    if not isinstance(payload, dict):
        raise SessionTokenError("Session token payload must be an object.")

    owner_id = payload.get("owner")
    if owner_id != expected_owner_id:
        raise SessionTokenError("Session token belongs to another owner.")

    store_session_id = payload.get("sid")
    if not isinstance(store_session_id, str) or not store_session_id:
        raise SessionTokenError("Session token is missing its session id.")

    return store_session_id
