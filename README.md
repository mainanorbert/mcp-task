# MCP Task

Simple chat application with a FastAPI backend and a Next.js frontend.

## Project Structure

```text
MCP-Task/
├── AGENTS.md
├── README.md
├── backend-mcp/
│   ├── main.py
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── Dockerfile
│   ├── .env.example
│   ├── api/
│   │   ├── router.py
│   │   ├── deps.py
│   │   └── routes/
│   │       ├── chat.py
│   │       └── health.py
│   ├── core/
│   │   ├── config.py
│   │   ├── logging.py
│   │   └── prompts.py
│   ├── schemas/
│   │   └── chat.py
│   ├── services/
│   │   └── chat_service.py
│   └── docs/
│       └── adr/
└── frontend-mcp/
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx
    │   ├── globals.css
    │   └── components/
    │       └── Chat.tsx
    ├── public/
    ├── package.json
    ├── package-lock.json
    ├── next.config.ts
    ├── tsconfig.json
    └── .env.example
```

## Architecture

### Backend: `backend-mcp/`

The backend is a FastAPI service organized by responsibility.

- `main.py`: Application entrypoint. Creates the FastAPI app, configures middleware, initializes shared clients, and includes routers. It should not contain business logic.
- `api/`: HTTP communication layer. Defines routes, dependencies, and request/response handling.
- `api/routes/chat.py`: Validates chat requests, delegates completion work to the service layer, and returns the assistant response.
- `api/routes/health.py`: Health check endpoint.
- `schemas/`: Pydantic request and response models.
- `services/`: Business logic independent of FastAPI.
- `services/chat_service.py`: Builds the OpenAI chat messages from system prompt plus conversation history and calls chat completions.
- `core/`: Shared infrastructure such as settings, logging, and prompts.
- `docs/adr/`: Architecture Decision Records.

### Frontend: `frontend-mcp/`

The frontend is a Next.js app that renders a minimal chat interface.

- `app/page.tsx`: Main page shell.
- `app/components/Chat.tsx`: Chat UI, local conversation history, API call, loading/error states, and markdown rendering for assistant replies.
- `app/layout.tsx`: Root layout.
- `app/globals.css`: Global styling.
- `public/`: Static assets.

## Chat Flow

1. The user sends a message from the frontend chat interface.
2. The frontend keeps prior `user` and `assistant` messages in local state.
3. The frontend posts the full message history to `POST /chat`.
4. The backend validates that the last message is from the user.
5. The backend calls the chat service with:
   - the system prompt
   - the previous conversation history
   - the latest user message
6. The chat service calls OpenAI chat completions.
7. The backend returns `{ "message": "..." }`.
8. The frontend appends the assistant response and renders it as markdown.

No tools or web-search services are used in the current phase.
