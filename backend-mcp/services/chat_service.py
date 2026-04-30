"""Chat orchestration: in-memory session + Meridian MCP agent.

The HTTP layer (``api/routes/chat.py``) calls :func:`handle_chat_turn`. This
function is the only place that knows how to:

  1. Look up (or create) the session in :class:`SessionStore`.
  2. Replay the stored history to the Meridian agent.
  3. Persist the latest user + assistant turns for the next call.

It has no FastAPI imports so it stays trivially testable.
"""

from __future__ import annotations

from core.logging import get_logger
from services.mcp_agent import AgentPromptTooLongError, AgentRunError, run_support_agent
from services.session_store import SessionStore

logger = get_logger(__name__)


class ChatServiceError(Exception):
    """Raised when the chat turn cannot be completed."""

    def __init__(self, message: str, *, status_code: int = 502) -> None:
        """Store a human-readable error and optional HTTP status for API mapping."""
        super().__init__(message)
        self.status_code = status_code


async def handle_chat_turn(
    *,
    session_store: SessionStore,
    session_id: str,
    user_message: str,
    model: str,
    instructions: str,
    mcp_server_url: str,
    mcp_timeout_seconds: int,
    max_turns: int,
) -> str:
    """Run one chat turn against the Meridian support agent.

    Args:
        session_store: The shared in-memory session store.
        session_id: Stable identifier for this conversation.
        user_message: Latest user message (already validated/non-empty).
        model: OpenAI model id.
        instructions: Agent system prompt.
        mcp_server_url: Streamable-HTTP MCP endpoint.
        mcp_timeout_seconds: HTTP read timeout for MCP.
        max_turns: Maximum agent loop iterations.

    Returns:
        The assistant reply.

    Raises:
        ChatServiceError: If the agent loop fails. Uses HTTP 400 when the prompt is
            over the token limit; otherwise the default status is 502.
    """
    session = await session_store.get_or_create(session_id)
    history = session.as_messages()

    try:
        reply = await run_support_agent(
            user_message=user_message,
            history=history,
            model=model,
            instructions=instructions,
            mcp_server_url=mcp_server_url,
            mcp_timeout_seconds=mcp_timeout_seconds,
            max_turns=max_turns,
        )
    except AgentPromptTooLongError as exc:
        logger.warning("chat_turn_failed_prompt_too_long session_id=%s", session_id)
        raise ChatServiceError(str(exc), status_code=400) from exc
    except AgentRunError as exc:
        logger.warning("chat_turn_failed session_id=%s error=%s", session_id, exc)
        raise ChatServiceError(str(exc)) from exc

    session.append("user", user_message)
    session.append("assistant", reply)
    return reply
