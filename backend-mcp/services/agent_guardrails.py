"""Input guardrails for the Meridian support :class:`agents.Agent`.

Token limits use ``tiktoken`` so counts align with OpenAI-style tokenization for
the configured chat model.
"""

from __future__ import annotations

from typing import Any

import tiktoken
from agents import GuardrailFunctionOutput
from agents.guardrail import InputGuardrail, input_guardrail

from core.logging import get_logger

logger = get_logger(__name__)

MAX_USER_PROMPT_TOKENS: int = 500
DEFAULT_TOKENIZER_MODEL: str = "gpt-4o-mini"
INPUT_TOKEN_GUARDRAIL_NAME: str = "max_500_prompt_tokens"


def _encoding_for_openai_model(model_name: str) -> tiktoken.Encoding:
    """Return a tiktoken encoding appropriate for the given OpenAI model id.

    Args:
        model_name: An OpenAI chat model id (e.g. ``gpt-4o-mini``).

    Returns:
        The tiktoken encoding instance used to count tokens.
    """
    try:
        return tiktoken.encoding_for_model(model_name)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_text_tokens(text: str, *, model_name: str) -> int:
    """Count how many tokens ``text`` would occupy for ``model_name``.

    Args:
        text: UTF-8 text to measure.
        model_name: Model id used to pick the tokenizer.

    Returns:
        Non-negative token count.
    """
    enc = _encoding_for_openai_model(model_name)
    return len(enc.encode(text))


def latest_user_message_text(agent_input: str | list[Any]) -> str:
    """Extract the newest user message text from runner input.

    The support turn always appends the latest user message last; the limit
    applies to that turn only (not the whole replayed history).

    Args:
        agent_input: Either a raw string or the message list passed to ``Runner.run``.

    Returns:
        The UTF-8 content string to tokenize, possibly empty if not found.
    """
    if isinstance(agent_input, str):
        return agent_input
    if not agent_input:
        return ""
    last = agent_input[-1]
    if isinstance(last, dict):
        content = last.get("content")
        if isinstance(content, str):
            return content
        return ""
    content = getattr(last, "content", None)
    if isinstance(content, str):
        return content
    return ""


@input_guardrail(name=INPUT_TOKEN_GUARDRAIL_NAME, run_in_parallel=False)
def guardrail_max_user_prompt_tokens(ctx: Any, agent: Any, message: str | list[Any]) -> GuardrailFunctionOutput:
    """Tripwire when the latest user turn exceeds ``MAX_USER_PROMPT_TOKENS`` tokens."""
    text = latest_user_message_text(message)
    raw_model = getattr(agent, "model", None)
    model_name = raw_model if isinstance(raw_model, str) else DEFAULT_TOKENIZER_MODEL
    n_tokens = count_text_tokens(text, model_name=model_name)
    over = n_tokens > MAX_USER_PROMPT_TOKENS
    if over:
        logger.info("input_token_guardrail_triggered tokens=%d max=%d", n_tokens, MAX_USER_PROMPT_TOKENS)
    return GuardrailFunctionOutput(
        output_info={"token_count": n_tokens, "max_tokens": MAX_USER_PROMPT_TOKENS},
        tripwire_triggered=over,
    )


# Static list for Agent(..., input_guardrails=...); extend when adding guardrails.
MERIDIAN_SUPPORT_INPUT_GUARDRAILS: list[InputGuardrail[Any]] = [guardrail_max_user_prompt_tokens]
