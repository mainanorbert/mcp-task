"""Meridian Electronics customer-support agent backed by an MCP server.

This module owns the OpenAI Agents SDK wiring: it builds the Streamable-HTTP
MCP server connection, constructs the support agent on each turn, and runs the
``Runner`` loop. It intentionally has zero FastAPI imports so it can be reused
from CLIs, scripts, or tests.
"""

from __future__ import annotations

from agents import Agent, Runner, trace
from agents.exceptions import InputGuardrailTripwireTriggered
from agents.mcp import MCPServerStreamableHttp

from core.logging import get_logger
from services.agent_guardrails import (
    INPUT_TOKEN_GUARDRAIL_NAME,
    MAX_USER_PROMPT_TOKENS,
    MERIDIAN_SUPPORT_INPUT_GUARDRAILS,
)

logger = get_logger(__name__)


class AgentRunError(Exception):
    """Raised when the agent loop fails (MCP connection error, model error, ...)."""


class AgentPromptTooLongError(AgentRunError):
    """Raised when the user message exceeds the configured token limit."""


def _build_mcp_server(
    *,
    url: str,
    timeout_seconds: int,
) -> MCPServerStreamableHttp:
    """Create a Streamable-HTTP MCP server pointing at the Meridian backend.

    ``cache_tools_list=True`` means the MCP ``tools/list`` request happens once
    per connection (fetched on first ``Runner.run`` step) rather than on every
    model step.
    """
    return MCPServerStreamableHttp(
        params={
            "url": url,
            "timeout": timeout_seconds,
        },
        name="meridian-mcp",
        cache_tools_list=True,
    )


async def run_support_agent(
    *,
    user_message: str,
    history: list[dict[str, str]],
    model: str,
    instructions: str,
    mcp_server_url: str,
    mcp_timeout_seconds: int,
    max_turns: int,
) -> str:
    """Run one conversational turn of the Meridian support agent.

    Args:
        user_message: The newest user message (plain text).
        history: Prior conversation turns as ``[{"role", "content"}, ...]``.
        model: OpenAI model id (e.g. ``"gpt-4o-mini"``).
        instructions: System prompt for the agent.
        mcp_server_url: Streamable-HTTP MCP endpoint.
        mcp_timeout_seconds: HTTP read timeout for MCP requests.
        max_turns: Hard cap on Agent loop iterations (tool calls + LLM steps).

    Returns:
        The final assistant text returned by the agent.

    Raises:
        AgentRunError: If the MCP connection or the agent run fails.
    """
    input_messages = list(history) + [{"role": "user", "content": user_message}]

    try:
        async with _build_mcp_server(
            url=mcp_server_url,
            timeout_seconds=mcp_timeout_seconds,
        ) as mcp_server:
            agent = Agent(
                name="MeridianSupport",
                instructions=instructions,
                model=model,
                mcp_servers=[mcp_server],
                input_guardrails=MERIDIAN_SUPPORT_INPUT_GUARDRAILS,
            )
            with trace("meridian_customer_support_turn"):
                result = await Runner.run(
                    agent,
                    input=input_messages,
                    max_turns=max_turns,
                )
    except InputGuardrailTripwireTriggered as exc:
        guardrail_name = exc.guardrail_result.guardrail.get_name()
        logger.warning("agent_run_blocked_input_guardrail name=%s", guardrail_name)
        # Map additional input guardrail names here when MERIDIAN_SUPPORT_INPUT_GUARDRAILS grows.
        if guardrail_name == INPUT_TOKEN_GUARDRAIL_NAME:
            raise AgentPromptTooLongError(
                f"Your message exceeds the maximum of {MAX_USER_PROMPT_TOKENS} tokens "
                "(model-aligned tokenizer count).",
            ) from exc
        raise AgentRunError("This message could not be processed due to a safety check.") from exc
    except Exception as exc:
        logger.warning(
            "agent_run_failed model=%s mcp=%s error=%r",
            model,
            mcp_server_url,
            exc,
        )
        raise AgentRunError("Customer support agent failed to respond.") from exc

    return result.final_output or ""
