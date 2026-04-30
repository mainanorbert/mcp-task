"""Unit tests for ``services.agent_guardrails`` helpers and limits."""

import unittest

from services.agent_guardrails import (
    MAX_USER_PROMPT_TOKENS,
    count_text_tokens,
    latest_user_message_text,
)


class LatestUserMessageTextTests(unittest.TestCase):
    """Behaviour of ``latest_user_message_text``."""

    def test_plain_string_is_returned(self) -> None:
        """A string input is treated as the user text."""
        self.assertEqual(latest_user_message_text("hello"), "hello")

    def test_last_dict_user_content(self) -> None:
        """The last list item's string content is returned."""
        msgs = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "ok"},
            {"role": "user", "content": "second"},
        ]
        self.assertEqual(latest_user_message_text(msgs), "second")


class TokenLimitTests(unittest.TestCase):
    """Token counting stays under the configured ceiling for normal prompts."""

    def test_short_message_under_limit(self) -> None:
        """Typical short text is below 500 tokens."""
        text = "What monitors do you sell?"
        n = count_text_tokens(text, model_name="gpt-4o-mini")
        self.assertLess(n, MAX_USER_PROMPT_TOKENS)

    def test_oversized_message_exceeds_limit(self) -> None:
        """A long repeated segment can exceed 500 tokens."""
        chunk = "meridian support question "
        text = chunk * 800
        n = count_text_tokens(text, model_name="gpt-4o-mini")
        self.assertGreater(n, MAX_USER_PROMPT_TOKENS)
