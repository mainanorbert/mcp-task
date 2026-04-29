"""Aggregate API routers for inclusion in the FastAPI application."""

from fastapi import APIRouter

from api.routes import chat, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(chat.router, tags=["chat"])
