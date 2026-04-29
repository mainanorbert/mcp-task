"""Health check HTTP routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Return a simple readiness payload for load balancers."""
    return {"status": "ok"}
