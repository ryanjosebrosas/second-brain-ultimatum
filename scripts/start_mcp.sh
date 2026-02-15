#!/bin/bash
# Start the Second Brain MCP server
# Usage: bash scripts/start_mcp.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env if it exists
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

echo "Starting Second Brain MCP Server..."
echo "  Model: ${ANTHROPIC_API_KEY:+Claude (API key set)}${ANTHROPIC_API_KEY:-WARNING: No API key}"
echo "  Mem0: ${MEM0_API_KEY:+Cloud}${MEM0_API_KEY:-Local}"
echo "  Supabase: ${SUPABASE_URL:-NOT SET}"

cd "$PROJECT_DIR"
python -m second_brain.mcp_server
