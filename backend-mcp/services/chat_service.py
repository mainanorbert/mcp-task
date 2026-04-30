"""OpenAI chat completion logic (no FastAPI imports)."""

from openai import APIError, AsyncOpenAI

from core.logging import get_logger

logger = get_logger(__name__)


class ChatCompletionError(Exception):
    """Raised when the upstream chat completion fails."""


async def complete_chat(
    *,
    client: AsyncOpenAI,
    model: str,
    system_prompt: str,
    conversation: list[dict[str, str]],
) -> str:
    """Call the chat completions API and return the assistant text content."""
    history = [{"role": h["role"], "content": h["content"]} for h in conversation]
    messages = [{"role": "system", "content": system_prompt}, *history]
    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=messages,
        )
    except APIError as exc:
        logger.warning("openai_chat_completion_failed model=%s error=%r", model, exc)
        raise ChatCompletionError("Upstream model request failed.") from exc

    choice = completion.choices[0].message
    return choice.content or ""
