### Naming
- **Files**: `snake_case.py`
- **Classes**: `PascalCase` — `BrainConfig`, `MemoryService`, `RecallResult`
- **Functions**: `snake_case` — `get_model()`, `search_memory()`
- **Constants**: `UPPER_SNAKE` — only for true constants
- **Agent instances**: `snake_case` — `recall_agent`, `ask_agent`

### Type Hints
- Use `str | None` syntax (Python 3.11+), not `Optional[str]`
- Use `TYPE_CHECKING` for circular import forward references:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from second_brain.services.memory import MemoryService
```

### Pydantic Models
- Use `Field(...)` for required fields, `Field(default=...)` for optional
- Add `description=` to every Field for LLM output models
- Group related fields with comments (`# LLM providers`, `# Supabase`, etc.)

### Imports
- Standard library first, third-party second, local third
- Lazy imports inside functions for optional/heavy dependencies
- Use absolute imports: `from second_brain.config import BrainConfig`

### Docstrings
- One-line for simple functions, multi-line only when non-obvious
- Class docstrings required, method docstrings only when logic is complex
