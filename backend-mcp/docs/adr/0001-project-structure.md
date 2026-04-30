# ADR 0001 – Project structure (backend)

- Status: Accepted
- Date: 2026-04-30

## Context

We are building the Phase 1 Meridian Electronics customer support API. The
top-level constraint from `AGENTS.md` is the FastAPI layered architecture:
`main.py` → `api/` → `services/` (business logic) with `core/` and `schemas/`
as supporting layers.

## Decision

Adopt the layered structure exactly as documented in `AGENTS.md`:

| Layer | Location | Holds |
| --- | --- | --- |
| Orchestrator | `main.py` | App factory, middleware, lifespan, router wiring. |
| Communication | `api/` | Routers, DI (`deps.py`), zero business logic. |
| Validation | `schemas/` | Pydantic request/response models. |
| Business logic | `services/` | `chat_service`, `mcp_agent`, `session_store`. No FastAPI imports. |
| Infrastructure | `core/` | `config.py`, `logging.py`, `prompts.py`. |
| Architecture docs | `architecture/` | (reserved) |
| Decision log | `docs/adr/` | This file. |

`services/` is split into three focused modules so each has one job:

- `session_store.py` – pure in-memory data structure (no I/O).
- `mcp_agent.py` – Agents SDK + MCP transport; reusable from CLI/scripts.
- `chat_service.py` – orchestration glue (loads session, runs agent, persists).

## Consequences

- The HTTP layer stays trivially testable; `chat.py` is ~30 lines.
- Swapping the in-memory `SessionStore` for Redis later is a one-file change.
- `mcp_agent.run_support_agent` can be reused from a future CLI without any
  FastAPI dependency.
