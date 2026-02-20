# Supabase PostgREST Schema Cache Fix

## Problem

After running migration `016_vault_ingestion.sql`, PostgREST's schema cache did not pick up:
- **New columns** on `knowledge_repo`: `author`, `client`, `content_type`, `vault_path`, `ingested_at`, `file_hash`
- **New table**: `vault_transcripts`

Every insert/upsert attempt returned:
```
PGRST204: Could not find the 'author' column of 'knowledge_repo' in the schema cache
```

And for the new table:
```
404: Could not find the relation 'vault_transcripts' in the schema cache
```

**Attempts that failed:**
1. `NOTIFY pgrst, 'reload schema'` — did not refresh the cache
2. `NOTIFY pgrst, 'reload config'` — did not refresh the cache
3. Restarting the Supabase project — did not refresh the cache
4. Dropping and recreating columns — did not refresh the cache
5. Creating a PostgreSQL RPC function (`upsert_vault_knowledge`) — function also not found in cache (`PGRST202`)

This is a known Supabase issue where `ALTER TABLE ADD COLUMN` and `CREATE TABLE` changes from migrations are not reflected in PostgREST's schema cache, even after restarts.

## Solution 1: Column Mapping (knowledge_repo)

**Bypass the broken columns entirely.** Map vault-specific fields into columns that PostgREST already knows about (from earlier migrations):

| Vault Field | Mapped To | How |
|------------|-----------|-----|
| `vault_path` | `source_file` | Direct mapping — same purpose |
| `content_type` | `category` | Direct mapping — defaults to `"vault"` if null |
| `author` | `tags` array | Encoded as `"author:luke"` |
| `client` | `tags` array | Encoded as `"client:eden"` |
| `file_hash` | `tags` array | Encoded as `"hash:abc123..."` |
| `ingested_at` | `created_at` | Uses Supabase default timestamp |

### Code (`storage.py` — `upsert_vault_knowledge`)

```python
async def upsert_vault_knowledge(self, data: dict) -> dict:
    tags = list(data.get("tags") or [])
    if data.get("author"):
        tags.append(f"author:{data['author']}")
    if data.get("client"):
        tags.append(f"client:{data['client']}")
    if data.get("file_hash"):
        tags.append(f"hash:{data['file_hash']}")

    row = {
        "title": data.get("title"),
        "content": data.get("content"),
        "category": data.get("content_type") or data.get("category") or "vault",
        "source_file": data.get("vault_path", data.get("source_file")),
        "tags": tags or None,
        "user_id": data.get("user_id", self.user_id),
    }
    if data.get("embedding"):
        row["embedding"] = data["embedding"]

    row = {k: v for k, v in row.items() if v is not None}
    query = self._client.table("knowledge_repo").upsert(
        row, on_conflict="category,source_file"
    )
    result = await asyncio.to_thread(query.execute)
    return result.data[0] if result.data else {}
```

### Additional Fix: NOT NULL constraint on `category`

Some vault files don't have a `content_type` classification (e.g., files outside known directory patterns). The `category` column has a NOT NULL constraint. Fixed by defaulting to `"vault"`:

```python
"category": data.get("content_type") or data.get("category") or "vault",
```

### Idempotency Fix: `.insert()` → `.upsert()`

Initial workaround used `.insert()` which caused `409 Conflict` on re-runs (unique constraint `knowledge_repo_unique_source` on `category, source_file`). Switched to `.upsert(row, on_conflict="category,source_file")` — PostgREST knows about this existing constraint, so upserts work correctly. Re-running ingestion now updates existing rows instead of failing.

## Solution 2: Table Redirect (vault_transcripts → knowledge_repo)

The `vault_transcripts` table (created in migration 016) is also invisible to PostgREST — returns 404 on any operation.

**Workaround**: Store transcripts in `knowledge_repo` with `category="transcript"` and pack transcript-specific fields into tags:

| Transcript Field | Mapped To | How |
|-----------------|-----------|-----|
| `summary` | `content` | Direct mapping |
| `source_file` | `source_file` | Direct mapping |
| `speaker` | `tags` array | Encoded as `"speaker:john"` |
| `duration` | `tags` array | Encoded as `"duration:45m"` |
| `word_count` | `tags` array | Encoded as `"words:5000"` |
| `title` | `title` | Falls back to `source_file` if missing |
| category | `category` | Fixed to `"transcript"` |

## Querying Vault Data

```sql
-- All vault content
SELECT * FROM knowledge_repo WHERE category NOT IN ('transcript');

-- All transcripts
SELECT * FROM knowledge_repo WHERE category = 'transcript';

-- Find entries by author
SELECT * FROM knowledge_repo WHERE 'author:luke' = ANY(tags);

-- Find entries for a client
SELECT * FROM knowledge_repo WHERE 'client:eden' = ANY(tags);

-- Transcripts by speaker
SELECT * FROM knowledge_repo
WHERE category = 'transcript' AND 'speaker:john' = ANY(tags);

-- Extract author from tags
SELECT title,
  (SELECT unnest(tags) WHERE unnest LIKE 'author:%') as author_tag
FROM knowledge_repo
WHERE source_file LIKE 'cc content system%';
```

## Future Fix

When PostgREST eventually picks up the new columns/tables (or after a full Supabase project recreation), revert both methods:

```python
# upsert_vault_knowledge — revert to proper columns:
query = self._client.table("knowledge_repo").upsert(
    data, on_conflict="vault_path"
)

# upsert_vault_transcript — revert to dedicated table:
query = self._client.table("vault_transcripts").upsert(
    data, on_conflict="source_file"
)
```

## Environment

- Supabase project: `<your-supabase-project-ref>`
- `supabase-py` version: latest (as of 2026-02-19)
- PostgREST schema cache: stale after migration 016
- Date: 2026-02-19
