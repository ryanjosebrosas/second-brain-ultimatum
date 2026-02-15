# Validation Prompt

> Use this after implementation to run the validation suite.
> Replace the commands with your project's actual tools.
>
> This covers Levels 1-4 of the 5-level validation pyramid (see `reference/validation-strategy.md`).
> Save validation results using the format in `templates/VALIDATION-REPORT-TEMPLATE.md`.
> For comprehensive technical review, also use `/code-review`. For process review, use `/system-review`.

---

Run comprehensive validation on the codebase. Execute these checks in order and report back.

### 1. Linting
```
{your lint command, e.g.: uv run ruff check src/}
```

### 2. Formatting
```
{your format check command, e.g.: uv run ruff format --check src/}
```

### 3. Type Checking
```
{your type check command, e.g.: uv run mypy src/}
```

### 4. Unit Tests
```
{your unit test command, e.g.: uv run pytest tests/ -m unit -v}
```

### 5. Integration Tests
```
{your integration test command, e.g.: uv run pytest tests/ -m integration -v}
```

## Report Format

Provide a concise summary:

```
Validation Results
---
Linting:          PASSED / FAILED (X issues)
Formatting:       PASSED / FAILED
Type Checking:    PASSED / FAILED (X errors)
Unit Tests:       PASSED / FAILED (X tests)
Integration Tests: PASSED / FAILED

Status: ALL PASSED / FAILED (list issues)
```

If issues found, list each with file name, line number, and description.
