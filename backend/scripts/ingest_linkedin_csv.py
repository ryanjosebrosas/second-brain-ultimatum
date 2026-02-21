"""Ingest LinkedIn CSV posts into the examples table.

Reads a CSV of high-performing LinkedIn posts and stores them as examples
so the content creation agent can reference them as style/voice patterns.

Usage:
    python scripts/ingest_linkedin_csv.py <csv_path> [--user-id uttam] [--dry-run]
"""
import asyncio
import csv
import logging
import os
import sys

if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def parse_csv(csv_path: str, min_length: int = 100) -> list[dict]:
    """Parse LinkedIn CSV into post dicts.

    Args:
        csv_path: Path to the CSV file.
        min_length: Minimum post length to include (filters out stubs).

    Returns:
        List of dicts with keys: account, content, post_url, hook.
    """
    posts = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header row
        logger.info("CSV headers: %s", header)

        for row in reader:
            if len(row) < 4:
                continue
            full_post = row[1].strip()
            account = row[2].strip()
            post_url = row[3].strip()

            if not full_post or not account or len(full_post) < min_length:
                continue

            # Extract hook (first line or first sentence)
            first_line = full_post.split("\n")[0].strip()
            hook = first_line[:150] if first_line else full_post[:150]

            posts.append({
                "account": account,
                "content": full_post,
                "post_url": post_url,
                "hook": hook,
            })

    return posts


async def ingest_posts(
    csv_path: str,
    user_id: str = "uttam",
    dry_run: bool = False,
    min_length: int = 100,
):
    """Ingest CSV posts into the examples table."""
    posts = parse_csv(csv_path, min_length=min_length)
    logger.info("Parsed %d posts from CSV", len(posts))

    if not posts:
        logger.warning("No valid posts found in CSV.")
        return

    # Group by account for logging
    from collections import Counter
    accounts = Counter(p["account"] for p in posts)
    for acc, cnt in accounts.most_common():
        logger.info("  %s: %d posts", acc, cnt)

    if dry_run:
        logger.info("DRY RUN -- would ingest %d posts. Exiting.", len(posts))
        for i, p in enumerate(posts[:5]):
            logger.info(
                "  Sample %d: [%s] %s...",
                i + 1, p["account"], p["hook"][:80],
            )
        return

    from second_brain.deps import create_deps
    deps = create_deps()

    if not deps.embedding_service:
        logger.error("Embedding service not available. Cannot ingest without embeddings.")
        return

    ingested = 0
    mem0_stored = 0
    errors = 0
    for i, post in enumerate(posts):
        # Embed the content for vector search
        try:
            embedding = await deps.embedding_service.embed_query(post["content"][:8000])
        except Exception as e:
            errors += 1
            logger.warning("Embedding failed for post %d: %s", i + 1, type(e).__name__)
            continue

        # Build example entry matching examples table schema
        example = {
            "content_type": "linkedin",
            "title": f"{post['account']} -- {post['hook'][:80]}",
            "content": post["content"],
            "source_file": post["post_url"],
            "tags": [post["account"], "linkedin"],
            "embedding": embedding,
        }

        try:
            result = await deps.storage_service.upsert_example(example)
            if result:
                ingested += 1
            else:
                errors += 1
                logger.warning("Failed to ingest post %d from %s", i + 1, post["account"])
        except Exception as e:
            errors += 1
            logger.warning("Error ingesting post %d: %s", i + 1, type(e).__name__)
            logger.debug("Detail: %s", e)

        # Store in Mem0 for semantic memory recall
        try:
            mem0_content = (
                f"LinkedIn post by {post['account']}:\n\n"
                f"{post['content'][:4000]}"
            )
            metadata = {
                "category": "linkedin_example",
                "source": post["account"],
                "post_url": post["post_url"],
                "hook": post["hook"],
            }
            await deps.memory_service.add(mem0_content, metadata=metadata)
            mem0_stored += 1
        except Exception as e:
            logger.warning("Mem0 store failed for post %d: %s", i + 1, type(e).__name__)
            logger.debug("Mem0 error detail: %s", e)

        # Progress log every 50 posts
        if (i + 1) % 50 == 0:
            logger.info("Progress: %d/%d ingested, %d in Mem0", ingested, len(posts), mem0_stored)

    logger.info(
        "Done -- %d/%d posts ingested, %d stored in Mem0, %d errors.",
        ingested, len(posts), mem0_stored, errors,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest LinkedIn CSV into examples table")
    parser.add_argument("csv_path", help="Path to the LinkedIn CSV file")
    parser.add_argument("--user-id", default="uttam", help="User ID for data ownership")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, don't write to DB")
    parser.add_argument("--min-length", type=int, default=100, help="Min post length to include")
    args = parser.parse_args()

    if not os.path.exists(args.csv_path):
        logger.error("CSV file not found: %s", args.csv_path)
        sys.exit(1)

    asyncio.run(ingest_posts(
        csv_path=args.csv_path,
        user_id=args.user_id,
        dry_run=args.dry_run,
        min_length=args.min_length,
    ))
