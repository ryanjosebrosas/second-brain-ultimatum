## Development Commands

### Install
```bash
cd backend
pip install -e ".[dev]"              # Core + dev dependencies
pip install -e ".[dev,graphiti]"     # + Graphiti knowledge graph
pip install -e ".[dev,subscription]" # + Claude Agent SDK (subscription auth)
```

### Run MCP Server
```bash
cd backend
python -m second_brain.mcp_server    # Start MCP server (for Claude Code)
```

### CLI
```bash
brain --help                         # Show CLI commands
brain migrate                        # Run data migration
brain health                         # Check brain health
```

### Tests
```bash
cd backend
pytest                               # All tests (~781)
pytest tests/test_agents.py          # Single file
pytest -k "test_recall"              # Filter by name
pytest -x                            # Stop on first failure
pytest -v                            # Verbose output
```

### Environment Setup
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your keys:
# ANTHROPIC_API_KEY, MEM0_API_KEY, SUPABASE_URL, SUPABASE_KEY,
# VOYAGE_API_KEY (optional), GRAPHITI_ENABLED=false
```

### Database Migrations
```bash
# Apply migrations via Supabase dashboard or CLI
# Migrations in: backend/supabase/migrations/ (001–014, numbered)
# New migrations: create backend/supabase/migrations/015_description.sql
```

### Reingest Knowledge Graph
```bash
cd backend
python scripts/reingest_graph.py     # Re-sync Graphiti graph from Mem0
```

### Docker (Full Stack)
```bash
# Start both backend + frontend
docker compose up -d

# Start backend only
docker compose up -d backend

# Start frontend only
docker compose up -d frontend

# View logs
docker compose logs -f

# Rebuild after code changes
docker compose up -d --build

# Stop everything
docker compose down
```
