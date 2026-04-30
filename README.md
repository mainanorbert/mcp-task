# Meridian Electronics – Customer Support Chatbot (Phase 1)

Production-ready, end-to-end AI customer support for **Meridian Electronics**:

- **Frontend** – Next.js 16 chat UI on Vercel.
- **Backend** – FastAPI service on Render.
- **Agent** – OpenAI Agents SDK (`gpt-4o-mini` by default).
- **Tools** – Loaded dynamically from the Meridian **MCP server** over Streamable HTTP.

The agent handles the four Phase 1 workflows from the brief:

1. **Product availability** – browse / search / fetch by SKU.
2. **Authentication** – verify customer by email + 4-digit PIN.
3. **Order history** – list a customer's orders, get one by id.
4. **Order placement** – confirm cart, then create the order.

```
┌──────────────┐   POST /chat    ┌────────────────┐  Agents SDK  ┌──────────┐  MCP   ┌─────────────┐
│  Next.js UI  │ ───────────────▶│  FastAPI app   │ ───────────▶│ MCP tools│ ─────▶ │ Meridian DB │
│ (Clerk auth) │ ◀───────────────│ (memory+agent) │ ◀───────────│  (8 of)  │ ◀───── │  (managed)  │
└──────────────┘   reply + sid   └────────────────┘             └──────────┘        └─────────────┘
```

---

## Repository layout

```text
mcp-task/
├── README.md                  ← you are here
├── AGENTS.md                  ← project-wide agent rules (FastAPI structure)
├── backend-mcp/               ← FastAPI + Agents SDK + MCP integration
└── frontend-mcp/              ← Next.js chat UI (Clerk-gated)
```

### `backend-mcp/` (FastAPI)

```text
backend-mcp/
├── main.py                ← ASGI entrypoint: app factory, CORS, request logging, lifespan
├── pyproject.toml         ← deps: fastapi, openai-agents, uvicorn, clerk, pydantic-settings
├── uv.lock
├── Dockerfile             ← Render-ready container (uv sync + uvicorn)
├── .env.example
├── api/
│   ├── router.py          ← aggregates resource routers
│   ├── deps.py            ← DI: session store, optional Clerk auth
│   └── routes/
│       ├── chat.py        ← POST /chat: validates input, delegates to chat_service
│       └── health.py      ← GET  /health: readiness probe
├── core/
│   ├── config.py          ← pydantic-settings: OPENAI_API_KEY, MCP_SERVER_URL, etc.
│   ├── logging.py         ← stdout JSON-friendly logger setup
│   └── prompts.py         ← Meridian system instructions (4 workflows)
├── schemas/
│   └── chat.py            ← ChatRequest, ChatResponse, HealthResponse
├── services/              ← ── BUSINESS LOGIC (no FastAPI imports) ──
│   ├── session_store.py   ← in-memory per-session memory (history + customer)
│   ├── mcp_agent.py       ← OpenAI Agents SDK + MCPServerStreamableHttp
│   └── chat_service.py    ← orchestration: load session → run agent → persist
├── tests/
│   ├── conftest.py        ← puts backend root on sys.path
│   └── unit/
│       ├── test_session_store.py
│       └── test_chat_service.py
├── architecture/          ← (reserved for diagrams – see AGENTS.md layer 6)
└── docs/adr/              ← Architecture Decision Records
```

#### What each folder does (per `AGENTS.md`)

| Layer | Folder | Responsibility |
| --- | --- | --- |
| 1. Orchestrator | `main.py` | Builds FastAPI, mounts routers, runs lifespan (no business logic). |
| 2. Communication | `api/` | HTTP endpoints + DI; thin layer that calls into `services/`. |
| 3. Validation | `schemas/` | Pydantic request/response models. |
| 4. Business logic | `services/` | `chat_service` + `mcp_agent` + `session_store`. Framework-agnostic. |
| 5. Infrastructure | `core/` | Config, logging, prompts. |
| 6. Architecture | `architecture/` | (reserved for system blueprints – Mermaid, etc.) |
| 7. Docs | `docs/adr/` | ADRs explaining design decisions. |

### `frontend-mcp/` (Next.js 16)

```text
frontend-mcp/
├── app/
│   ├── layout.tsx              ← root shell, Clerk provider, header, fonts
│   ├── page.tsx                ← landing: shows Chat (signed-in) or sign-in CTA
│   ├── globals.css
│   └── components/Chat.tsx     ← chat UI: history, suggested prompts, markdown render,
│                                  POSTs `{messages, session_id}`, persists returned `session_id`
├── proxy.ts                    ← Clerk middleware (Next 16 renamed `middleware` → `proxy`)
├── package.json                ← Next 16, React 19, Clerk, Tailwind 4
├── next.config.ts
├── tsconfig.json
├── public/
└── .env.example
```

---

## Chat flow (end-to-end)

1. User signs in with Clerk on the Next.js UI.
2. User types a message; the UI sends `POST /chat` with:
   - `Authorization: Bearer <clerk_jwt>` (when signed in)
   - JSON body `{ "session_id": <prior or null>, "messages": [...] }`
3. `api/routes/chat.py` validates and resolves a `session_id`:
   - Explicit body value if present, else `user:<clerk_sub>`, else a fresh uuid.
4. `services/chat_service.handle_chat_turn`:
   - Loads the session from `SessionStore` (in-memory).
   - Replays prior history to the agent.
5. `services/mcp_agent.run_support_agent`:
   - Opens a Streamable-HTTP connection to the Meridian MCP server.
   - Builds an `Agent` with the Meridian system prompt and `mcp_servers=[…]`.
   - Runs `Runner.run(agent, input=history+latest_user)` (`max_turns=20`).
   - The agent autonomously selects/executes MCP tools (e.g. `verify_customer_pin`, `create_order`).
6. The reply is persisted to the session and returned as `{message, session_id}`.
7. The UI appends the reply and remembers `session_id` for the next turn.

---

## Local development

### Backend

```bash
cd backend-mcp
cp .env.example .env          # then fill OPENAI_API_KEY at minimum
uv sync
uv run uvicorn main:app --reload --port 8000
# health → http://localhost:8000/health
```

For local testing without Clerk set `REQUIRE_AUTH=false` in `.env`.

### Frontend

```bash
cd frontend-mcp
cp .env.example .env.local    # then fill NEXT_PUBLIC_API_URL + Clerk keys
npm install
npm run dev                   # http://localhost:3000
```

### Tests

```bash
cd backend-mcp
uv run python -m pytest tests/ -v
```

---

## Deployment

### Backend (Render – Docker)

- Service type: **Web Service** (Docker).
- Root directory: `backend-mcp`, Dockerfile path: `Dockerfile`.
- Required env vars: `OPENAI_API_KEY`, `MCP_SERVER_URL`, `CORS_ORIGINS`,
  `CLERK_JWKS_URL`, `CLERK_AUTHORIZED_PARTIES`.
- Health check path: `/health`.

### Frontend (Vercel)

- Project root: `frontend-mcp`.
- Env vars: `NEXT_PUBLIC_API_URL` (your Render URL),
  `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`.

---

## Configuration reference

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | *(required)* | OpenAI key used by the Agents SDK. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model the agent runs on. Switch to `gpt-4o` for higher quality. |
| `MCP_SERVER_URL` | `https://order-mcp-74afyau24q-uc.a.run.app/mcp` | Streamable-HTTP MCP endpoint. |
| `MCP_REQUEST_TIMEOUT_SECONDS` | `30` | HTTP read timeout for MCP. |
| `AGENT_MAX_TURNS` | `20` | Max tool/LLM iterations per chat turn. |
| `LOG_LEVEL` | `INFO` | Process-wide logging level. |
| `CORS_ORIGINS` | localhost + Vercel + Render | Comma-separated allowed origins. |
| `REQUIRE_AUTH` | `true` | If `false`, `/chat` is public (local dev only). |
| `CLERK_JWKS_URL` | – | Clerk JWKS endpoint for JWT validation. |
| `CLERK_AUTHORIZED_PARTIES` | – | Comma-separated Clerk `azp` allow-list. |

---

## Phase 1 success criteria – status

- [x] Connect to MCP server (Streamable HTTP).
- [x] Discover available tools (`cache_tools_list=True`).
- [x] Single agent that converts user input → tool selection → tool call.
- [x] Workflows: product availability, authentication, order history, order placement.
- [x] Simple Next.js chat UI (input + output, suggested prompts, markdown).
- [x] In-memory session memory (history + logged-in customer).
- [x] Backend + frontend ready for deploy (Dockerfile + `vercel`-ready Next 16).
