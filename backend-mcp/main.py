"""ASGI entrypoint: FastAPI factory, middleware, lifespan, and router wiring only."""

import os
import time
from uuid import uuid4
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI

from api.router import api_router
from core.config import get_settings, parse_cors_origins
from core.logging import configure_logging, get_logger

logger = get_logger(__name__)


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
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = api_key
    client = AsyncOpenAI(api_key=api_key)
    app.state.openai_client = client
    logger.info("application_startup model=%s", settings.openai_model)
    try:
        yield
    finally:
        await client.close()
        logger.info("application_shutdown")


def create_app() -> FastAPI:
    """Build the FastAPI application with CORS and mounted API routers."""
    settings = get_settings()
    configure_logging(settings.log_level)
    app = FastAPI(
        title="Chat API",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
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
