"""Unit tests for chat completion service behavior."""

import sys
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

sys.modules.setdefault(
    "openai",
    SimpleNamespace(APIError=Exception, AsyncOpenAI=object),
)

from services.chat_service import complete_chat


class CompleteChatTests(IsolatedAsyncioTestCase):
    async def test_complete_chat_sends_system_prompt_and_history(self):
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=AsyncMock(
                        return_value=SimpleNamespace(
                            choices=[
                                SimpleNamespace(
                                    message=SimpleNamespace(content="Hello there")
                                )
                            ]
                        )
                    )
                )
            )
        )
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello"},
            {"role": "user", "content": "Remember me?"},
        ]

        result = await complete_chat(
            client=client,
            model="test-model",
            system_prompt="You are helpful.",
            conversation=history,
        )

        self.assertEqual(result, "Hello there")
        client.chat.completions.create.assert_awaited_once_with(
            model="test-model",
            messages=[
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello"},
                {"role": "user", "content": "Remember me?"},
            ],
        )
