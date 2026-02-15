```bash
# Install (editable, with dev deps)
pip install -e ".[dev]"

# Run tests
python -m pytest tests/ -v

# CLI commands (requires .env with API keys)
python -m second_brain.cli recall "content patterns"
python -m second_brain.cli ask "Help me write an email"
python -m second_brain.cli migrate

# MCP server (for Claude Code)
python -m second_brain.mcp_server

# Verify imports
python -c "from second_brain import __version__; print(f'v{__version__}')"
python -c "from second_brain.config import BrainConfig; print('Config OK')"
python -c "from second_brain.agents import recall_agent, ask_agent; print('Agents OK')"
```
