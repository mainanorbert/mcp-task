"""ASGI entrypoint: FastAPI factory, middleware, lifespan, and router wiring only.

This file deliberately contains no business logic. Its responsibilities are:

* Build the FastAPI app (``create_app``).
* Configure CORS + structured request/response logging middleware.
* Spin up shared application state in the lifespan (in-memory ``SessionStore``,
  ensure ``OPENAI_API_KEY`` is set for the Agents SDK).
* Mount the API routers from :mod:`api.router`.
"""

import os
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.router import api_router
from core.config import get_settings, parse_cors_origins
from core.logging import configure_logging, get_logger
from services.session_store import SessionStore

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize shared state on startup and clean up on shutdown."""
    settings = get_settings()

    api_key = settings.openai_api_key.strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is missing or empty. "
            "Set it in your hosting environment (Render/Vercel/etc.) and redeploy."
        )
    os.environ.setdefault("OPENAI_API_KEY", api_key)

    app.state.session_store = SessionStore()
    logger.info(
        "application_startup model=%s mcp_url=%s require_auth=%s",
        settings.openai_model,
        settings.mcp_server_url,
        settings.require_auth,
    )
    try:
        yield
    finally:
        logger.info(
            "application_shutdown sessions=%d",
            await app.state.session_store.size(),
        )


def create_app() -> FastAPI:
    """Build the FastAPI application with CORS and mounted API routers."""
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="Meridian Electronics Support API",
        version="0.2.0",
        description=(
            "Customer support chatbot backed by the OpenAI Agents SDK and the "
            "Meridian Electronics MCP server."
        ),
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        """Add a request id, log start/finish, and timing for every HTTP request."""
        request_id = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["x-request-id"] = request_id
            return response
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
                request_id,
                request.method,
                request.url.path,
                status_code,
                duration_ms,
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
