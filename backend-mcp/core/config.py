"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Runtime configuration for the chat API."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = Field(
        default="",
        description="OpenAI API key (set OPENAI_API_KEY in Render → Environment)",
    )
    openai_model: str = Field(default="gpt-4.1-mini", description="Chat model id")
    log_level: str = Field(default="INFO", description="Python logging level")
    cors_origins: str = Field(
        default="http://localhost:3000,https://frontend-mcp-chi.vercel.app,https://mcp-task-1.onrender.com",
        description="Comma-separated browser origins allowed for CORS",
    )
    web_agent_max_turns: int = Field(
        default=25,
        ge=1,
        le=80,
        description="Max agent loop turns when use_web_search is enabled",
    )
    mcp_playwright_session_timeout_seconds: float = Field(
        default=120.0,
        ge=15.0,
        description="MCP client read timeout for the Playwright stdio server",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings parsed from the environment."""
    return Settings()


def parse_cors_origins(raw: str) -> list[str]:
    """Split a comma-separated CORS origins string into a list of trimmed URLs."""
    return [part.strip() for part in raw.split(",") if part.strip()]
