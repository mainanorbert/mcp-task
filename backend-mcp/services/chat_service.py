"""OpenAI chat completion logic (no FastAPI imports)."""

from openai import APIError, AsyncOpenAI


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
        raise ChatCompletionError("Upstream model request failed.") from exc

    choice = completion.choices[0].message
    return choice.content or ""
