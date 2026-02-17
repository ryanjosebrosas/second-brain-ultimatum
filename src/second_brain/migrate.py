"""Migrate markdown Second Brain data to Mem0 + Supabase."""

import asyncio
import logging
from pathlib import Path

from second_brain.config import BrainConfig
from second_brain.services.memory import MemoryService
from second_brain.services.storage import StorageService

logger = logging.getLogger(__name__)


class BrainMigrator:
    """Migrate markdown Second Brain data to Mem0 + Supabase."""

    def __init__(self, config: BrainConfig, embedding_service=None):
        self.config = config
        self.data_path = config.brain_data_path
        self.memory = MemoryService(config)
        self.storage = StorageService(config)
        self.embedding = embedding_service

    async def _get_embedding(self, text: str) -> list[float] | None:
        """Generate embedding if service available. Non-critical."""
        if not self.embedding:
            return None
        try:
            return await self.embedding.embed(text[:8000])
        except Exception as e:
            logger.debug("Embedding generation failed (non-critical): %s", e)
            return None

    async def migrate_all(self):
        """Run full migration with error tracking."""
        logger.info(f"Migrating from {self.data_path}")
        results = {"success": 0, "skipped": 0, "errors": 0}
        try:
            await self.migrate_memory_content(results)
            await self.migrate_patterns(results)
            await self.migrate_experiences(results)
            await self.migrate_examples(results)
            await self.migrate_knowledge_repo(results)
            logger.info(
                "Migration complete! Success: %d, Skipped: %d, Errors: %d",
                results["success"], results["skipped"], results["errors"],
            )
        except Exception as e:
            logger.error("Migration failed: %s. Partial data may exist.", e)
            raise

    async def migrate_memory_content(self, results: dict | None = None):
        """Migrate memory/ folders to Mem0 + Supabase memory_content table."""
        if results is None:
            results = {"success": 0, "skipped": 0, "errors": 0}
        categories = [
            ("company", ["products.md", "positioning.md", "differentiators.md"]),
            ("customers", ["ideal-customer-profile.md", "pain-points.md", "objections.md"]),
            ("audience", ["ideal-client.md", "pain-points.md", "objections.md"]),
            ("style-voice", ["tone-guide.md", "vocabulary.md", "structure.md", "examples.md"]),
            ("values-beliefs", ["core-values.md", "frameworks.md", "principles.md", "povs.md"]),
            ("personal", ["expertise.md", "services.md", "positioning.md", "differentiators.md", "bio.md"]),
        ]
        for category, files in categories:
            for filename in files:
                filepath = self.data_path / "memory" / category / filename
                if not filepath.exists():
                    results["skipped"] += 1
                    continue
                try:
                    content = filepath.read_text(encoding="utf-8")
                    # Add to Mem0 (semantic)
                    await self.memory.add(
                        content,
                        metadata={"category": category, "source": str(filepath)},
                    )
                    # Generate embedding (non-critical)
                    embedding = await self._get_embedding(content)
                    # Add to Supabase (structured, upsert for idempotency)
                    data = {
                        "category": category,
                        "subcategory": filepath.stem,
                        "title": filepath.stem.replace("-", " ").title(),
                        "content": content,
                        "source_file": str(filepath),
                    }
                    if embedding is not None:
                        data["embedding"] = embedding
                    await self.storage.upsert_memory_content(data)
                    results["success"] += 1
                    logger.info(f"Migrated: {category}/{filename}")
                except Exception as e:
                    results["errors"] += 1
                    logger.warning("Failed to migrate %s/%s: %s", category, filename, e)

    async def migrate_patterns(self, results: dict | None = None):
        """Migrate memory/patterns/ to Supabase patterns table."""
        if results is None:
            results = {"success": 0, "skipped": 0, "errors": 0}
        patterns_dir = self.data_path / "memory" / "patterns"
        if not patterns_dir.exists():
            logger.warning(f"Patterns directory not found: {patterns_dir}")
            return

        for pattern_file in patterns_dir.glob("*.md"):
            if pattern_file.name == "INDEX.md":
                continue
            content = pattern_file.read_text(encoding="utf-8")
            patterns = self._parse_patterns(content, str(pattern_file))
            for p in patterns:
                try:
                    embedding = await self._get_embedding(p.get("pattern_text", ""))
                    if embedding is not None:
                        p["embedding"] = embedding
                    await self.storage.upsert_pattern(p)
                    await self.memory.add(
                        f"Pattern: {p['name']}\n{p['pattern_text']}",
                        metadata={"type": "pattern", "topic": p["topic"]},
                    )
                    results["success"] += 1
                except Exception as e:
                    results["errors"] += 1
                    logger.warning("Failed to migrate pattern '%s': %s", p.get("name"), e)
            logger.info(f"Migrated {len(patterns)} patterns from {pattern_file.name}")

    async def migrate_experiences(self, results: dict | None = None):
        """Migrate experiences/ folders to Supabase experiences table."""
        if results is None:
            results = {"success": 0, "skipped": 0, "errors": 0}
        exp_dir = self.data_path / "experiences"
        if not exp_dir.exists():
            logger.warning(f"Experiences directory not found: {exp_dir}")
            return

        for category_dir in exp_dir.iterdir():
            if not category_dir.is_dir() or category_dir.name == "INDEX.md":
                continue
            for project_dir in category_dir.iterdir():
                if not project_dir.is_dir():
                    continue
                try:
                    experience = {
                        "name": project_dir.name,
                        "category": category_dir.name,
                        "source_path": str(project_dir),
                    }
                    for key, filename in [
                        ("plan_summary", "plan.md"),
                        ("learnings", "learnings.md"),
                    ]:
                        filepath = project_dir / filename
                        if filepath.exists():
                            experience[key] = filepath.read_text(encoding="utf-8")[:5000]
                    await self.storage.add_experience(experience)
                    results["success"] += 1
                    logger.info(f"Migrated experience: {project_dir.name}")
                except Exception as e:
                    results["errors"] += 1
                    logger.warning("Failed to migrate experience '%s': %s", project_dir.name, e)

    async def migrate_examples(self, results: dict | None = None):
        """Migrate memory/examples/ folders to Supabase examples table.

        Supports any content type subdirectory — content_type is derived from
        the directory name (e.g., memory/examples/case-study/ → content_type="case-study").
        """
        if results is None:
            results = {"success": 0, "skipped": 0, "errors": 0}
        examples_dir = self.data_path / "memory" / "examples"
        if not examples_dir.exists():
            logger.warning(f"Examples directory not found: {examples_dir}")
            return

        skip_files = {"INDEX.md", "README.md", ".gitkeep"}
        for type_dir in examples_dir.iterdir():
            if not type_dir.is_dir():
                continue
            content_type = type_dir.name
            for md_file in type_dir.glob("*.md"):
                if md_file.name in skip_files:
                    continue
                try:
                    content = md_file.read_text(encoding="utf-8")
                    title = md_file.stem.replace("-", " ").title()
                    await self.memory.add(
                        content,
                        metadata={"type": "example", "content_type": content_type},
                    )
                    embedding = await self._get_embedding(content)
                    data = {
                        "content_type": content_type,
                        "title": title,
                        "content": content,
                        "source_file": str(md_file),
                    }
                    if embedding is not None:
                        data["embedding"] = embedding
                    await self.storage.upsert_example(data)
                    results["success"] += 1
                    logger.info(f"Migrated example: {content_type}/{md_file.name}")
                except Exception as e:
                    results["errors"] += 1
                    logger.warning("Failed to migrate example '%s/%s': %s", content_type, md_file.name, e)

    async def migrate_knowledge_repo(self, results: dict | None = None):
        """Migrate memory/knowledge-repo/ folders to Supabase knowledge_repo table."""
        if results is None:
            results = {"success": 0, "skipped": 0, "errors": 0}
        repo_dir = self.data_path / "memory" / "knowledge-repo"
        if not repo_dir.exists():
            logger.warning(f"Knowledge repo directory not found: {repo_dir}")
            return

        skip_files = {"INDEX.md", "README.md", ".gitkeep", "_template.md"}
        for category_dir in repo_dir.iterdir():
            if not category_dir.is_dir():
                continue
            category = category_dir.name
            for md_file in category_dir.glob("*.md"):
                if md_file.name in skip_files:
                    continue
                try:
                    content = md_file.read_text(encoding="utf-8")
                    title = md_file.stem.replace("-", " ").title()
                    await self.memory.add(
                        content,
                        metadata={"type": "knowledge", "category": category},
                    )
                    embedding = await self._get_embedding(content)
                    data = {
                        "category": category,
                        "title": title,
                        "content": content,
                        "source_file": str(md_file),
                    }
                    if embedding is not None:
                        data["embedding"] = embedding
                    await self.storage.upsert_knowledge(data)
                    results["success"] += 1
                    logger.info(f"Migrated knowledge: {category}/{md_file.name}")
                except Exception as e:
                    results["errors"] += 1
                    logger.warning("Failed to migrate knowledge '%s/%s': %s", category, md_file.name, e)

    def _parse_patterns(self, content: str, source_file: str) -> list[dict]:
        """Parse markdown pattern file into structured pattern dicts."""
        patterns = []
        current: dict = {}
        for line in content.split("\n"):
            if line.startswith("### ") and not line.startswith("### Reference"):
                if current.get("name"):
                    patterns.append(current)
                current = {
                    "name": line[4:].strip(),
                    "source_file": source_file,
                    "pattern_text": "",
                    "topic": "Process",  # default
                }
            elif line.startswith("**Confidence**:") and current:
                current["confidence"] = line.split(":")[-1].strip()
            elif line.startswith("**Source**:") and current:
                current["source_experience"] = line.split(":", 1)[-1].strip()
            elif line.startswith("**Date**:") and current:
                date_str = line.split(":", 1)[-1].strip().split(",")[0].strip()
                current["date_added"] = date_str
            elif line.startswith("**Pattern**:") and current:
                current["_in_pattern"] = True
            elif line.startswith("**Evidence**:") and current:
                current["_in_pattern"] = False
                current["_in_evidence"] = True
                current["evidence"] = []
            elif line.startswith("**Anti-Pattern**:") and current:
                current["_in_evidence"] = False
                current["_in_anti"] = True
                current["anti_patterns"] = []
            elif current.get("_in_pattern") and line.strip():
                current["pattern_text"] += line.strip() + " "
            elif current.get("_in_evidence") and line.startswith("- "):
                current["evidence"].append(line[2:].strip())
            elif current.get("_in_anti") and line.startswith("- "):
                current.setdefault("anti_patterns", []).append(line[2:].strip())

        if current.get("name"):
            patterns.append(current)

        # Clean up internal flags
        for p in patterns:
            for key in ["_in_pattern", "_in_evidence", "_in_anti"]:
                p.pop(key, None)
            p["pattern_text"] = p.get("pattern_text", "").strip()

        return patterns


async def run_migration():
    """Entry point for migration."""
    config = BrainConfig()
    embedding = None
    if config.voyage_api_key or config.openai_api_key:
        try:
            from second_brain.services.embeddings import EmbeddingService
            embedding = EmbeddingService(config)
        except Exception as e:
            logger.warning("EmbeddingService not available for migration: %s", e)
    migrator = BrainMigrator(config, embedding_service=embedding)
    await migrator.migrate_all()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_migration())
