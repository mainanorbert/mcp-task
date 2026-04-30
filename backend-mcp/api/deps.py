"""FastAPI dependencies for request-scoped services."""

from functools import lru_cache

from fastapi import HTTPException, Request, status
from fastapi_clerk_auth import (  # type: ignore
    ClerkConfig,
    ClerkHTTPBearer,
    HTTPAuthorizationCredentials,
)
from openai import AsyncOpenAI

from core.config import get_settings, parse_clerk_authorized_parties


def get_openai_client(request: Request) -> AsyncOpenAI:
    """Return the shared AsyncOpenAI client stored on application state."""
    return request.app.state.openai_client


@lru_cache
def get_clerk_guard() -> ClerkHTTPBearer:
    """Return a cached Clerk bearer-token validator."""
    settings = get_settings()
    jwks_url = settings.clerk_jwks_url.strip()
    if not jwks_url:
        raise RuntimeError("CLERK_JWKS_URL is required for authenticated routes.")
    return ClerkHTTPBearer(ClerkConfig(jwks_url=jwks_url))


async def require_clerk_auth(request: Request) -> HTTPAuthorizationCredentials:
    """Validate the Clerk bearer token and return decoded credentials."""
    try:
        credentials = await get_clerk_guard()(request)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    if credentials is None or not credentials.decoded:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    authorized_parties = parse_clerk_authorized_parties(
        get_settings().clerk_authorized_parties
    )
    authorized_party = credentials.decoded.get("azp")
    if authorized_parties and authorized_party not in authorized_parties:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token authorized party is not allowed.",
        )

    return credentials
