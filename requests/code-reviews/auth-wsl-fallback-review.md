# Code Review: Auth WSL Fallback + Migration Constraint

- **Mode**: Parallel (4 agents)
- **Files Modified**: 2 (`auth.py`, `007_foreign_keys_indexes.sql`)
- **Files Deleted**: 19 (old execution reports + plan files — cleanup, not reviewed)
- **Total Findings**: 12 (Critical: 0, Major: 4, Minor: 8)

---

## Findings by Severity

### Major

#### 1. Hard-coded `DEFAULT_CONFIG_DIR` in Linux fallback — ignores caller's `config_dir`
```yaml
severity: major
category: Architecture
file: backend/src/second_brain/auth.py:120
issue: Linux fallback ignores config_dir parameter passed to get_oauth_token()
detail: >
  get_oauth_token(config_dir=...) threads config_path to _read_windows_credentials on Windows,
  but _read_linux_secret_service() hard-codes DEFAULT_CONFIG_DIR in its fallback. Callers passing
  a custom config_dir (e.g., tests using tmp_path) are silently ignored on Linux.
suggestion: >
  Add config_dir parameter to _read_linux_secret_service() and thread config_path from
  get_oauth_token(). Match the API contract of the other platform functions.
```

#### 2. Silent security downgrade from keyring to plaintext file
```yaml
severity: major
category: Security
file: backend/src/second_brain/auth.py:115-120
issue: Fallback from Secret Service to .credentials.json logged at debug level only
detail: >
  When secret-tool fails for ANY reason (not just missing — also daemon crash, DBUS failure,
  timeout), the code silently falls to reading a plaintext JSON file. On a real Linux desktop,
  a temporary keyring outage causes a security downgrade with no warning. FileNotFoundError
  (expected in WSL) should be distinguished from other failures (unexpected).
suggestion: >
  Split exception handling: FileNotFoundError -> logger.debug (expected WSL).
  Other OSError/TimeoutExpired -> logger.warning (unexpected degradation).
  Log the fallback itself at warning level.
```

#### 3. Duplicate/conflicting uniqueness on patterns.name
```yaml
severity: major
category: Architecture
file: backend/supabase/migrations/007_foreign_keys_indexes.sql:6-7
issue: New UNIQUE constraint overlaps with existing case-insensitive unique index from migration 003
detail: >
  003_pattern_constraints.sql creates CREATE UNIQUE INDEX idx_patterns_name_unique ON patterns(lower(name))
  (case-insensitive). 007 adds ADD CONSTRAINT patterns_name_unique UNIQUE (name) (case-sensitive).
  Two overlapping but non-equivalent uniqueness guards. The plain UNIQUE may be needed for FK
  reference target (Postgres requires it), but this should be documented.
suggestion: >
  Add a comment in 007 explaining the distinction: 003 enforces case-insensitive dedup,
  007 adds formal constraint for FK referential integrity. Verify both are needed.
```

#### 4. Missing index on confidence_history.pattern_name
```yaml
severity: major
category: Performance
file: backend/supabase/migrations/007_foreign_keys_indexes.sql:14-30
issue: FK added on confidence_history.pattern_name but no supporting index (growth_log has one)
detail: >
  growth_log gets idx_growth_log_pattern_name, but confidence_history has no equivalent index.
  ON DELETE CASCADE from patterns will require a full table scan of confidence_history.
suggestion: >
  Add: CREATE INDEX IF NOT EXISTS idx_confidence_history_pattern_name
    ON confidence_history(pattern_name);
```

---

### Minor

#### 5. No file permission check on .credentials.json (Linux)
```yaml
severity: minor
category: Security
file: backend/src/second_brain/auth.py:57-76
issue: Credentials file read without verifying restrictive permissions on Linux
detail: >
  _read_windows_credentials (now also called on Linux) reads the file without checking
  stat permissions. On a multi-user Linux system, a world-readable file exposes the OAuth token.
  On Windows this is less of a concern due to NTFS ACLs.
suggestion: >
  On Linux, check stat permissions before reading. Warn if group/other readable.
  Consider: import stat; if file_stat.st_mode & (stat.S_IRGRP | stat.S_IROTH): warn.
```

#### 6. Unguarded `.strip()` on Any-typed value from json.loads
```yaml
severity: minor
category: Type Safety
file: backend/src/second_brain/auth.py:71
issue: token from json.loads chain is Any; .strip() could raise AttributeError
detail: >
  data.get("claudeAiOauth", {}).get("accessToken") returns Any.
  If the value is unexpectedly an int/list/dict, .strip() raises AttributeError
  which is not caught by the existing except clause.
suggestion: >
  Add isinstance(token, str) guard before calling .strip(), or add AttributeError
  to the except tuple.
```

#### 7. Missing test for Linux fallback path
```yaml
severity: minor
category: Architecture
file: backend/tests/test_auth.py
issue: No test covers the new Linux-to-credentials.json fallback branch
detail: >
  The primary behavioral change (WSL fallback) has no test exercising it.
  Project convention: new code paths require new tests.
suggestion: >
  Add test where subprocess.run raises FileNotFoundError on Linux,
  verify _read_windows_credentials is called with correct config_dir.
```

#### 8. NOT IN subquery in cleanup DELETEs
```yaml
severity: minor
category: Performance
file: backend/supabase/migrations/007_foreign_keys_indexes.sql:2-3
issue: NOT IN with subquery is null-unsafe and optimizer-unfriendly
detail: >
  DELETE FROM growth_log WHERE pattern_name NOT IN (SELECT name FROM patterns)
  uses NOT IN which can produce unexpected results with NULLs and may prevent
  hash anti-join optimization in some Postgres versions.
suggestion: >
  Replace with NOT EXISTS:
  DELETE FROM growth_log gl
  WHERE NOT EXISTS (SELECT 1 FROM patterns p WHERE p.name = gl.pattern_name);
```

#### 9. Migration constraint not idempotent
```yaml
severity: minor
category: Security (operational)
file: backend/supabase/migrations/007_foreign_keys_indexes.sql:6-7
issue: ADD CONSTRAINT without IF NOT EXISTS guard
detail: >
  If migration 007 is re-run (CI reset, branch re-apply), it will fail on
  "constraint already exists", potentially leaving subsequent FK/RLS migrations unapplied.
suggestion: >
  Wrap in DO $$ BEGIN ... EXCEPTION WHEN duplicate_table THEN NULL; END $$;
```

#### 10. Removed migration header comment
```yaml
severity: minor
category: Architecture
file: backend/supabase/migrations/007_foreign_keys_indexes.sql:1
issue: Header comment block removed; inconsistent with other migration files
detail: >
  All other migrations (003, 005, etc.) have a descriptive header block.
  007 now starts directly with the DELETE statement.
suggestion: Restore a brief header comment describing the migration's purpose.
```

#### 11. Double filesystem stat (exists + read_text)
```yaml
severity: minor
category: Performance
file: backend/src/second_brain/auth.py:62-67
issue: creds_path.exists() then creds_path.read_text() is one unnecessary syscall
detail: >
  The exists() check can be eliminated by catching FileNotFoundError in the
  existing except clause (OSError already covers it).
suggestion: Remove exists() check; let read_text() raise FileNotFoundError naturally.
```

#### 12. No explicit type annotation on DEFAULT_CONFIG_DIR
```yaml
severity: minor
category: Type Safety
file: backend/src/second_brain/auth.py:20
issue: Module-level constant lacks explicit type annotation
detail: Type is correctly inferred as Path, but explicit annotation is best practice.
suggestion: "DEFAULT_CONFIG_DIR: Path = Path.home() / '.claude'"
```

---

## Summary Assessment

- **Overall**: Needs minor fixes
- **Recommended action**: Fix the 4 Major issues before committing; minor issues are optional improvements

### Priority Actions
1. **Thread `config_dir` through `_read_linux_secret_service()`** — API consistency bug
2. **Add `idx_confidence_history_pattern_name` index** — missing FK supporting index
3. **Distinguish `FileNotFoundError` from other failures in fallback logging** — security clarity
4. **Document or resolve duplicate uniqueness constraints** — migration clarity
