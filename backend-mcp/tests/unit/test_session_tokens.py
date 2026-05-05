"""Unit tests for signed client session tokens."""

import unittest

from core.session_tokens import (
    SessionTokenError,
    create_session_token,
    parse_session_token,
)


class SessionTokenTests(unittest.TestCase):
    """Signed session tokens are bound to one authenticated owner."""

    def test_token_round_trips_for_matching_owner(self) -> None:
        """A valid token returns its internal store session id."""
        token = create_session_token(
            store_session_id="user:user_123:abc",
            owner_id="user:user_123",
            secret="test-secret",
        )

        self.assertEqual(
            parse_session_token(
                token,
                expected_owner_id="user:user_123",
                secret="test-secret",
            ),
            "user:user_123:abc",
        )

    def test_token_rejects_different_owner(self) -> None:
        """A token minted for one Clerk user is invalid for another."""
        token = create_session_token(
            store_session_id="user:user_123:abc",
            owner_id="user:user_123",
            secret="test-secret",
        )

        with self.assertRaises(SessionTokenError):
            parse_session_token(
                token,
                expected_owner_id="user:user_456",
                secret="test-secret",
            )

    def test_token_rejects_tampering(self) -> None:
        """Changing any signed segment invalidates the token."""
        token = create_session_token(
            store_session_id="user:user_123:abc",
            owner_id="user:user_123",
            secret="test-secret",
        )
        tampered = f"{token[:-1]}x"

        with self.assertRaises(SessionTokenError):
            parse_session_token(
                tampered,
                expected_owner_id="user:user_123",
                secret="test-secret",
            )
