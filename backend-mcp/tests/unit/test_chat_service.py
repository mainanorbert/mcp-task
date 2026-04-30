"""Unit tests for ``services.chat_service.handle_chat_turn``.

The Agents SDK and MCP server are mocked out so the test does not require
network access or an OpenAI API key.
"""

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

from services.chat_service import ChatServiceError, handle_chat_turn
from services.mcp_agent import AgentRunError
from services.session_store import SessionStore


class HandleChatTurnTests(IsolatedAsyncioTestCase):
    """End-to-end behaviour of the chat orchestration service."""

    async def test_first_turn_persists_user_and_assistant_messages(self) -> None:
        """A fresh session is created and both messages end up in history."""
        store = SessionStore()
        with patch(
            "services.chat_service.run_support_agent",
            new=AsyncMock(return_value="Sure, here are our monitors..."),
        ) as mocked:
            reply = await handle_chat_turn(
                session_store=store,
                session_id="user:1",
                user_message="What monitors do you sell?",
                model="gpt-4o-mini",
                instructions="<system>",
                mcp_server_url="http://mcp.test/mcp",
                mcp_timeout_seconds=10,
                max_turns=5,
            )

        self.assertEqual(reply, "Sure, here are our monitors...")
        mocked.assert_awaited_once()
        kwargs = mocked.await_args.kwargs
        self.assertEqual(kwargs["history"], [])
        self.assertEqual(kwargs["user_message"], "What monitors do you sell?")

        session = await store.get_or_create("user:1")
        self.assertEqual(
            session.as_messages(),
            [
                {"role": "user", "content": "What monitors do you sell?"},
                {"role": "assistant", "content": "Sure, here are our monitors..."},
            ],
        )

    async def test_second_turn_replays_prior_history_to_agent(self) -> None:
        """Stored history is forwarded so the agent has short-term memory."""
        store = SessionStore()
        session = await store.get_or_create("user:1")
        session.append("user", "Hi")
        session.append("assistant", "Hello, how can I help?")

        with patch(
            "services.chat_service.run_support_agent",
            new=AsyncMock(return_value="Order placed."),
        ) as mocked:
            await handle_chat_turn(
                session_store=store,
                session_id="user:1",
                user_message="Place an order for SKU-123, qty 1.",
                model="gpt-4o-mini",
                instructions="<system>",
                mcp_server_url="http://mcp.test/mcp",
                mcp_timeout_seconds=10,
                max_turns=5,
            )

        history_arg = mocked.await_args.kwargs["history"]
        self.assertEqual(
            history_arg,
            [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello, how can I help?"},
            ],
        )

    async def test_agent_failure_is_wrapped(self) -> None:
        """``AgentRunError`` is translated to ``ChatServiceError`` and history is unchanged."""
        store = SessionStore()
        with patch(
            "services.chat_service.run_support_agent",
            new=AsyncMock(side_effect=AgentRunError("boom")),
        ):
            with self.assertRaises(ChatServiceError):
                await handle_chat_turn(
                    session_store=store,
                    session_id="user:1",
                    user_message="hi",
                    model="gpt-4o-mini",
                    instructions="<system>",
                    mcp_server_url="http://mcp.test/mcp",
                    mcp_timeout_seconds=10,
                    max_turns=5,
                )

        session = await store.get_or_create("user:1")
        self.assertEqual(session.as_messages(), [])
