"""FastAPI dependencies for request-scoped services."""

from fastapi import Request
from openai import AsyncOpenAI


def get_openai_client(request: Request) -> AsyncOpenAI:
    """Return the shared AsyncOpenAI client stored on application state."""
    return request.app.state.openai_client
