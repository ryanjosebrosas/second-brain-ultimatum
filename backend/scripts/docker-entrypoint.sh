#!/bin/bash
set -e

# --- Pre-flight checks ---
MISSING=""
[ -z "$SUPABASE_URL" ] && MISSING="$MISSING SUPABASE_URL"
[ -z "$SUPABASE_KEY" ] && MISSING="$MISSING SUPABASE_KEY"

if [ -n "$MISSING" ]; then
  echo "FATAL: Missing required env vars:$MISSING"
  echo "Ensure backend/.env is mounted or env vars are set in docker-compose.yml"
  exit 1
fi

# Warn about optional but important vars
[ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OPENAI_API_KEY" ] && [ -z "$GROQ_API_KEY" ] && \
  echo "WARNING: No LLM API key set (ANTHROPIC_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY). Agent calls will fail."

echo "Starting Second Brain services..."

uvicorn second_brain.api.main:app --host 0.0.0.0 --port "${API_PORT:-8001}" --log-level info &
API_PID=$!

python -m second_brain.mcp_server &
MCP_PID=$!

wait -n $API_PID $MCP_PID
EXIT_CODE=$?

echo "A service exited with code $EXIT_CODE, shutting down..."
kill $API_PID $MCP_PID 2>/dev/null || true
wait
exit $EXIT_CODE
