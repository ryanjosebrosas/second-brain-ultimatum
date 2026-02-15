### Framework
- **pytest** + **pytest-asyncio** with `asyncio_mode = "auto"`
- Run: `python -m pytest tests/ -v`

### Structure
```
tests/
├── conftest.py          # Shared fixtures: brain_config, mock_memory, mock_storage, mock_deps
├── test_services.py     # MemoryService + StorageService unit tests
├── test_migrate.py      # Migration tool tests (uses tmp_path)
├── test_agents.py       # Agent schema + tool registration tests
└── test_mcp_server.py   # MCP tool function tests
```

### Patterns
- **Always mock external services** — Mem0, Supabase, LLM calls
- Use `conftest.py` fixtures, never duplicate mock setup across files
- Use `tmp_path` for filesystem tests (migration, markdown parsing)
- Agent tests verify schema validation and tool registration, not LLM output

### Example
```python
@patch("second_brain.services.memory.Memory")
async def test_search(self, mock_memory_cls, mock_config):
    mock_client = MagicMock()
    mock_client.search.return_value = [{"memory": "test", "score": 0.95}]
    mock_memory_cls.from_config.return_value = mock_client
    service = MemoryService(mock_config)
    results = await service.search("test query")
    assert len(results) == 1
```
