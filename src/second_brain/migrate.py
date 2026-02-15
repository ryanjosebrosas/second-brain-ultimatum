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

    def __init__(self, config: BrainConfig):
        self.config = config
        self.data_path = config.brain_data_path
        self.memory = MemoryService(config)
        self.storage = StorageService(config)

    async def migrate_all(self):
        """Run full migration."""
        logger.info(f"Migrating from {self.data_path}")
        await self.migrate_memory_content()
        await self.migrate_patterns()
        await self.migrate_experiences()
        logger.info("Migration complete!")

    async def migrate_memory_content(self):
        """Migrate memory/ folders to Mem0 + Supabase memory_content table."""
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
                if filepath.exists():
                    content = filepath.read_text(encoding="utf-8")
                    # Add to Mem0 (semantic)
                    await self.memory.add(
                        content,
                        metadata={"category": category, "source": str(filepath)},
                    )
                    # Add to Supabase (structured)
                    await self.storage.upsert_memory_content({
                        "category": category,
                        "subcategory": filepath.stem,
                        "title": filepath.stem.replace("-", " ").title(),
                        "content": content,
                        "source_file": str(filepath),
                    })
                    logger.info(f"Migrated: {category}/{filename}")

    async def migrate_patterns(self):
        """Migrate memory/patterns/ to Supabase patterns table."""
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
                await self.storage.upsert_pattern(p)
                # Also add to Mem0 for semantic search
                await self.memory.add(
                    f"Pattern: {p['name']}\n{p['pattern_text']}",
                    metadata={"type": "pattern", "topic": p["topic"]},
                )
            logger.info(f"Migrated {len(patterns)} patterns from {pattern_file.name}")

    async def migrate_experiences(self):
        """Migrate experiences/ folders to Supabase experiences table."""
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
                experience = {
                    "name": project_dir.name,
                    "category": category_dir.name,
                    "source_path": str(project_dir),
                }
                # Read available files
                for key, filename in [
                    ("plan_summary", "plan.md"),
                    ("learnings", "learnings.md"),
                ]:
                    filepath = project_dir / filename
                    if filepath.exists():
                        experience[key] = filepath.read_text(encoding="utf-8")[:5000]
                await self.storage.add_experience(experience)
                logger.info(f"Migrated experience: {project_dir.name}")

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
    migrator = BrainMigrator(config)
    await migrator.migrate_all()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_migration())
