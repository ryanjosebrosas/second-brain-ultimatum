# ── Build stage ───────────────────────────────────────────
FROM python:3.12-slim AS builder
WORKDIR /app

# Install uv from official image (pinned version for reproducibility)
COPY --from=ghcr.io/astral-sh/uv:0.6.16 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy dependency files first (layer cache — only rebuilds when deps change)
COPY pyproject.toml uv.lock ./

# Install dependencies only (no project install yet — better layer caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-dev

# Copy source and install project
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# ── Runtime stage ─────────────────────────────────────────
FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# curl for HEALTHCHECK
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy virtual env from builder (contains all installed packages)
COPY --from=builder /app/.venv /app/.venv

# Copy source
COPY src/ ./src/
COPY pyproject.toml ./

# Activate venv by putting it first on PATH
ENV PATH="/app/.venv/bin:$PATH"

# Non-root user
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --no-create-home --shell /bin/false appuser && \
    mkdir -p /data && chown appuser:appuser /data

USER appuser

# Default transport for Docker
ENV MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    BRAIN_DATA_PATH=/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "second_brain.mcp_server"]
