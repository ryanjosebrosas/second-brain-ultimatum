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
    uv sync --locked --no-install-project --no-dev --extra subscription

# Copy source and install project
COPY src/ ./src/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --extra subscription

# ── Runtime stage ─────────────────────────────────────────
FROM python:3.12-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install curl (healthcheck) + Node.js (Claude CLI)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl gnupg && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    npm install -g @anthropic-ai/claude-code && \
    rm -rf /var/lib/apt/lists/*

# Copy virtual env from builder (contains all installed packages)
COPY --from=builder /app/.venv /app/.venv

# Copy source and entrypoint
COPY src/ ./src/
COPY pyproject.toml ./
COPY scripts/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

# Activate venv by putting it first on PATH
ENV PATH="/app/.venv/bin:$PATH"

# Non-root user + Claude CLI config scaffold
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --create-home --shell /bin/bash appuser && \
    mkdir -p /data && chown appuser:appuser /data && \
    mkdir -p /home/appuser/.claude/debug && \
    echo '{}' > /home/appuser/.claude/remote-settings.json && \
    echo '{}' > /home/appuser/.claude/settings.json && \
    chown -R appuser:appuser /home/appuser/.claude

USER appuser

# Default transport for Docker
ENV MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=8000 \
    BRAIN_DATA_PATH=/data

EXPOSE 8000 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health && curl -f http://localhost:8001/api/health/metrics || exit 1

CMD ["bash", "/app/docker-entrypoint.sh"]
