"""ASGI entrypoint: FastAPI factory, middleware, lifespan, and router wiring only."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from api.router import api_router
from core.config import get_settings, parse_cors_origins


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create shared clients on startup and release them on shutdown."""
    settings = get_settings()
    api_key = settings.openai_api_key.strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing or empty. In Render: Dashboard → your Web "
            "Service → Environment → add OPENAI_API_KEY, then redeploy."
        )
    client = AsyncOpenAI(api_key=api_key)
    app.state.openai_client = client
    try:
        yield
    finally:
        await client.close()


def create_app() -> FastAPI:
    """Build the FastAPI application with CORS and mounted API routers."""
    settings = get_settings()
    app = FastAPI(
        title="Chat API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=parse_cors_origins(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()

__all__ = ["app", "create_app"]
