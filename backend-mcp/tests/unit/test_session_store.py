"""Unit tests for the in-memory session store."""

from unittest import IsolatedAsyncioTestCase

from services.session_store import MAX_HISTORY, Session, SessionStore


class SessionTests(IsolatedAsyncioTestCase):
    """Behavior of the simple Session dataclass."""

    def test_append_and_serialize_history(self) -> None:
        """append() preserves order; as_messages() returns Agents-SDK dicts."""
        session = Session(session_id="s1")
        session.append("user", "hi")
        session.append("assistant", "hello")
        self.assertEqual(
            session.as_messages(),
            [
                {"role": "user", "content": "hi"},
                {"role": "assistant", "content": "hello"},
            ],
        )

    def test_history_is_capped_to_max_history(self) -> None:
        """Only the last MAX_HISTORY turns are kept."""
        session = Session(session_id="s1")
        for i in range(MAX_HISTORY + 5):
            session.append("user", f"msg-{i}")
        self.assertEqual(len(session.history), MAX_HISTORY)
        self.assertEqual(session.history[0].content, "msg-5")
        self.assertEqual(session.history[-1].content, f"msg-{MAX_HISTORY + 4}")


class SessionStoreTests(IsolatedAsyncioTestCase):
    """Behavior of the async SessionStore registry."""

    async def test_get_or_create_returns_same_instance(self) -> None:
        """Two lookups for the same id return the same Session object."""
        store = SessionStore()
        a = await store.get_or_create("user:42")
        b = await store.get_or_create("user:42")
        self.assertIs(a, b)
        self.assertEqual(await store.size(), 1)

    async def test_reset_drops_session(self) -> None:
        """reset() forgets the session and a fresh one is created next time."""
        store = SessionStore()
        first = await store.get_or_create("user:1")
        first.customer_id = "cust-9"
        await store.reset("user:1")
        second = await store.get_or_create("user:1")
        self.assertIsNot(first, second)
        self.assertIsNone(second.customer_id)

    async def test_reset_by_prefix_drops_only_matching_sessions(self) -> None:
        """Owner-scoped logout cleanup leaves unrelated sessions alone."""
        store = SessionStore()
        await store.get_or_create("user:1:a")
        await store.get_or_create("user:1:b")
        await store.get_or_create("user:2:a")

        reset_count = await store.reset_by_prefix("user:1:")

        self.assertEqual(reset_count, 2)
        self.assertEqual(await store.size(), 1)
