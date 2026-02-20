#!/bin/bash
set -e

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
