"""Web research via Playwright MCP and the OpenAI Agents SDK (no FastAPI imports)."""

from agents import Agent, Runner
from agents.mcp import MCPServerStdio
from agents.models.openai_provider import OpenAIProvider
from agents.tracing import trace
from openai import AsyncOpenAI

from core.prompts import get_web_investigator_instructions


class WebInvestigatorError(Exception):
    """Raised when the browser-based investigator agent fails."""


def build_investigator_task(messages: list[tuple[str, str]]) -> str:
    """Format recent chat turns into a single task string for the investigator."""
    if not messages:
        return ""
    lines = [f"{role.upper()}: {content}" for role, content in messages]
    return "\n".join(lines)


async def run_web_investigator(
    *,
    openai_client: AsyncOpenAI,
    model_name: str,
    user_task: str,
    max_turns: int,
    mcp_session_timeout_seconds: float,
) -> str:
    """Spawn Playwright MCP, run an investigator agent, and return the final text output."""
    playwright_params: dict = {
        "command": "npx",
        "args": ["-y", "@playwright/mcp@latest"],
    }
    provider = OpenAIProvider(openai_client=openai_client, use_responses=False)
    model = provider.get_model(model_name)
    try:
        async with MCPServerStdio(
            params=playwright_params,
            name="playwright",
            client_session_timeout_seconds=mcp_session_timeout_seconds,
        ) as mcp_browser:
            agent = Agent(
                name="investigator",
                instructions=get_web_investigator_instructions(),
                model=model,
                mcp_servers=[mcp_browser],
            )
            with trace("web_investigate"):
                result = await Runner.run(agent, user_task, max_turns=max_turns)
    except Exception as exc:
        raise WebInvestigatorError(
            "Web investigator failed (ensure Node.js/npx is installed and outbound network is "
            f"allowed). Details: {exc!r}"
        ) from exc

    final = result.final_output
    if isinstance(final, str):
        return final
    return str(final)
