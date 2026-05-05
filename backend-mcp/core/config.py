"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Runtime configuration for the Meridian Electronics support API."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(
        default="",
        description="OpenAI API key (set OPENAI_API_KEY in your hosting environment)",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model id used by the agent (gpt-4o-mini = cost-effective MVP)",
    )
    mcp_server_url: str = Field(
        default="https://order-mcp-74afyau24q-uc.a.run.app/mcp",
        description="Streamable-HTTP MCP server exposing Meridian internal services",
    )
    mcp_request_timeout_seconds: int = Field(
        default=30,
        description="HTTP read timeout for the MCP transport",
    )
    agent_max_turns: int = Field(
        default=20,
        description="Maximum tool/LLM loops per chat turn",
    )
    log_level: str = Field(default="INFO", description="Python logging level")
    cors_origins: str = Field(
        default="http://localhost:3000,https://frontend-mcp-chi.vercel.app,https://mcp-task-1.onrender.com",
        description="Comma-separated browser origins allowed for CORS",
    )
    clerk_jwks_url: str = Field(default="", description="Clerk JWKS endpoint")
    clerk_authorized_parties: str = Field(
        default="",
        description="Comma-separated allowed Clerk authorized party origins",
    )
    require_auth: bool = Field(
        default=True,
        description="When False, the /chat route is open (useful for local testing without Clerk).",
    )
    session_signing_secret: str = Field(
        default="",
        description=(
            "Secret used to HMAC-sign browser session ids. Falls back to "
            "OPENAI_API_KEY when empty."
        ),
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings parsed from the environment."""
    return Settings()


def parse_cors_origins(raw: str) -> list[str]:
    """Split a comma-separated CORS origins string into a list of trimmed URLs."""
    return [part.strip() for part in raw.split(",") if part.strip()]


def parse_clerk_authorized_parties(raw: str) -> set[str]:
    """Split configured Clerk authorized parties into normalized origins."""
    return {part.strip() for part in raw.split(",") if part.strip()}
