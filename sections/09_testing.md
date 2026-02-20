## Testing

**Framework**: pytest + pytest-asyncio (`asyncio_mode = "auto"` — all async tests run without decorator)

**Structure**: One test file per source module in `backend/tests/`
```
tests/
  conftest.py              # Shared fixtures (deps, mocked services, config)
  test_agents.py           # Agent behavior tests
  test_mcp_server.py       # MCP tool endpoint tests
  test_schemas.py          # Pydantic model validation tests
  test_services.py         # Service layer tests
  test_service_mcp.py      # Service-MCP bridge tests
  test_models.py           # AI model selection tests
  test_models_sdk.py       # Claude SDK model tests
  test_config.py           # Config loading tests
  test_auth.py             # Auth tests
  test_deps.py             # Dependency injection tests
  test_migrate.py          # Migration utility tests
  test_cli.py              # CLI command tests
  test_graph.py            # Graph service tests
  test_graphiti_service.py # Graphiti integration tests
  test_graphiti_memory.py  # Graphiti memory provider tests
  test_voyage.py           # Voyage AI service tests
  test_projects.py         # Project lifecycle tests
  test_operations.py       # Operations agent tests
  test_agentic.py          # Multi-agent pipeline tests
  test_chief_of_staff.py   # Routing orchestrator tests
  test_content_pipeline.py # Content pipeline tests
  test_foundation.py       # Foundation/smoke tests
  test_providers.py        # Provider registry tests
  test_provider_fallback_chains.py  # Fallback chain tests
  test_api.py              # REST API endpoint tests
```

**Approach**: Primarily unit tests with mocked external services (Mem0, Supabase, Voyage AI). Integration tests for service layer. REST API tests via FastAPI TestClient. No browser/UI tests.

**Run Tests**:
```bash
cd backend
pytest                          # All tests
pytest tests/test_agents.py     # Specific file
pytest -k "test_recall"         # Filter by name
pytest -x                       # Stop on first failure
```

**Commit Discipline**: Test count is tracked per commit (e.g., "781 total"). Never reduce count without explanation. New agents/tools require new tests.
