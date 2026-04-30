# ADR 0002 – Two-level authentication strategy

- Status: Accepted
- Date: 2026-04-30

## Context

The Meridian Electronics chatbot has **two** distinct identities to manage:

1. **Application user** – the person using the chat UI (must not be a random
   bot, deserves an isolated session, etc.).
2. **Meridian customer** – the customer record stored behind the MCP server,
   identified by email + 4-digit PIN, which is what unlocks order workflows.

These are conceptually different: the same app user might never authenticate
as a Meridian customer, or they might log into multiple customer accounts.

## Decision

- **App user auth** is handled by **Clerk** (existing setup, JWT bearer tokens
  validated against Clerk's JWKS in `api/deps.py`). Clerk's `sub` is used as
  the default `session_id` so every user has a stable, isolated server-side
  conversation memory.
- **Meridian customer auth** is handled by the **agent** itself, by calling
  the MCP tool `verify_customer_pin(email, pin)` per the system prompt
  (Workflow 2). The returned `customer_id` is implicitly carried in the
  agent's working context for the rest of the session via the recent-history
  replay performed by `chat_service`.

For local development without Clerk, set `REQUIRE_AUTH=false`. The route then
falls back to a per-request anonymous session id (`anon:<uuid>`).

## Consequences

- The HTTP layer enforces "who can talk to the bot" (Clerk).
- The agent enforces "who is this customer" (PIN). This matches the brief
  ("basic: email + PIN check using test data").
- We never persist customer credentials anywhere – only the verified
  `customer_id` lives in process memory until the session is evicted.
- Replacing Clerk with another IdP is a one-file change in `api/deps.py`.
