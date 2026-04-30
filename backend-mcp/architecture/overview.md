# System architecture

High-level views of the Meridian customer-support stack: **Next.js** (Clerk) → **FastAPI** (OpenAI Agents SDK + in-memory sessions) → **OpenAI** and the **Meridian MCP** tool server.

---

## Components and data flow

```mermaid
---
title: Meridian support stack – logical architecture
---
flowchart TB
  U["End user"]

  subgraph client["Frontend – Next.js (Vercel)"]
    UI["Chat UI"]
    CL["Clerk authentication"]
  end

  subgraph backend["Backend – FastAPI (Render)"]
    direction TB
    HTTP["api/routes – POST /chat, GET /health"]
    CS["chat_service – orchestration"]
    SS["session_store – in-memory history"]
    MA["mcp_agent – Agents SDK Runner + MCP client"]
    GR["agent_guardrails – 500-token input limit"]
    HTTP --> CS
    CS --> SS
    CS --> MA
    MA --> GR
  end

  subgraph external["External services"]
    OAI["OpenAI API – chat + tool orchestration"]
    MCP["Meridian MCP server – Streamable HTTP tools"]
  end

  U --> UI
  UI --> CL
  UI -->|"POST /chat (session + messages)"| HTTP
  MA --> OAI
  MA --> MCP

  style U fill:#f4f4f5,stroke:#a1a1aa
  style client fill:#eff6ff,stroke:#3b82f6
  style backend fill:#f0fdf4,stroke:#22c55e
  style external fill:#fef3c7,stroke:#d97706
```

**Notes**

- The browser sends only the latest user line per turn; **session history** is replayed from `session_store` on the server.
- **MCP tools** (catalog, auth, orders, etc.) are discovered over **Streamable HTTP** and invoked by the agent loop.
- **Input guardrails** run before the main model step (`run_in_parallel=false`) so oversized prompts fail fast with HTTP 400.

---

## Chat turn (sequence)

```mermaid
---
title: One POST /chat turn – simplified sequence
---
sequenceDiagram
  autonumber
  actor User as User
  participant FE as Next.js chat
  participant API as FastAPI /chat
  participant Svc as chat_service
  participant Mem as session_store
  participant Run as mcp_agent Runner
  participant OAI as OpenAI
  participant MCP as Meridian MCP

  User->>FE: send message
  FE->>API: POST /chat
  API->>Svc: handle_chat_turn
  Svc->>Mem: get_or_create(session_id)
  Svc->>Run: run_support_agent(history + message)
  Run->>Run: input guardrails token check
  Run->>OAI: agent turn model + tools
  loop MCP tool calls
    Run->>MCP: tool request
    MCP-->>Run: tool result
  end
  OAI-->>Run: final assistant text
  Run-->>Svc: reply string
  Svc->>Mem: append user + assistant
  Svc-->>API: reply
  API-->>FE: ChatResponse JSON
  FE-->>User: show reply
```

---

## Backend layering (FastAPI package)

```mermaid
---
title: backend-mcp – internal layering
---
flowchart LR
  subgraph L2["Layer 2 – HTTP"]
    R["api/router + routes"]
    D["api/deps – DI"]
  end

  subgraph L3["Layer 3 – contracts"]
    SC["schemas"]
  end

  subgraph L4["Layer 4 – domain"]
    CH["chat_service"]
    AG["mcp_agent"]
    SE["session_store"]
    GU["agent_guardrails"]
  end

  subgraph L5["Layer 5 – infra"]
    CO["core/config"]
    LO["core/logging"]
    PR["core/prompts"]
  end

  R --> D
  R --> SC
  R --> CH
  CH --> SE
  CH --> AG
  AG --> GU
  CH --> CO
  AG --> CO
  AG --> PR
```

This mirrors the layout described in the project `README` and `AGENTS.md`.
