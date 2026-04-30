"""Minimal in-memory session storage for Phase 1 of the Meridian chatbot.

The Phase 1 challenge calls for "minimal memory" that keeps:
  * the recent conversation (so the model has short-term context), and
  * the logged-in user (so the agent does not have to re-authenticate
    every turn once verify_customer_pin has succeeded).

This implementation is intentionally simple: a process-local dict guarded by an
async lock. Sessions evict the oldest items when ``MAX_HISTORY`` is exceeded.
For a multi-replica deployment you would swap this module for Redis or a DB,
but the public API stays the same.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

MAX_HISTORY = 40


@dataclass
class ChatTurn:
    """One stored turn in a chat session."""

    role: str
    content: str


@dataclass
class Session:
    """In-memory state for a single chat session."""

    session_id: str
    history: list[ChatTurn] = field(default_factory=list)
    customer_id: Optional[str] = None
    customer_email: Optional[str] = None

    def append(self, role: str, content: str) -> None:
        """Append a turn and trim history to ``MAX_HISTORY`` items."""
        self.history.append(ChatTurn(role=role, content=content))
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]

    def as_messages(self) -> list[dict[str, str]]:
        """Return history as the dict format consumed by the Agents SDK."""
        return [{"role": t.role, "content": t.content} for t in self.history]


class SessionStore:
    """Async-safe registry of chat sessions keyed by ``session_id``."""

    def __init__(self) -> None:
        """Create an empty store with its own asyncio lock."""
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def get_or_create(self, session_id: str) -> Session:
        """Return the session for ``session_id``, creating it on first use."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                session = Session(session_id=session_id)
                self._sessions[session_id] = session
            return session

    async def reset(self, session_id: str) -> None:
        """Drop the session entirely (used by a future "log out" action)."""
        async with self._lock:
            self._sessions.pop(session_id, None)

    async def size(self) -> int:
        """Return the number of currently tracked sessions (for diagnostics)."""
        async with self._lock:
            return len(self._sessions)
