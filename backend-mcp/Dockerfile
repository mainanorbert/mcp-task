# Render: set root directory to this folder, Dockerfile path `Dockerfile`.
# Render injects `PORT`; default below matches common local checks.

FROM python:3.12-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv

# Lockfile layer: reinstall only when dependencies change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY main.py ./
COPY api ./api/
COPY core ./core/
COPY schemas ./schemas/
COPY services ./services/

RUN uv sync --frozen --no-dev

ENV PORT=10000

EXPOSE 10000

CMD ["sh", "-c", "uv run uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
