"""Health check HTTP routes."""

from fastapi import APIRouter

from schemas.chat import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return a simple readiness payload for load balancers and uptime checks."""
    return HealthResponse()
