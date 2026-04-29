"""OpenAI chat completion logic (no FastAPI imports)."""

from collections.abc import AsyncIterator

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
    messages = [{"role": "system", "content": system_prompt}, *conversation]
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


async def stream_chat(
    *,
    client: AsyncOpenAI,
    model: str,
    system_prompt: str,
    conversation: list[dict[str, str]],
) -> AsyncIterator[str]:
    """Stream assistant text deltas from the chat completions API."""
    messages = [{"role": "system", "content": system_prompt}, *conversation]
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except APIError as exc:
        logger.warning("openai_chat_stream_failed model=%s error=%r", model, exc)
        raise ChatCompletionError("Upstream model request failed.") from exc
