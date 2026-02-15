"""Unit tests for BrainMigrator."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

from second_brain.config import BrainConfig
from second_brain.migrate import BrainMigrator


@pytest.fixture
def mock_config(tmp_path):
    """Config with test markdown structure in tmp_path."""
    # Create test markdown structure
    memory_dir = tmp_path / "memory" / "company"
    memory_dir.mkdir(parents=True)
    (memory_dir / "products.md").write_text("# Products\nTest product info")

    patterns_dir = tmp_path / "memory" / "patterns"
    patterns_dir.mkdir(parents=True)
    (patterns_dir / "INDEX.md").write_text("# Index")
    (patterns_dir / "test-patterns.md").write_text(
        "### Test Pattern\n\n"
        "**Confidence**: LOW\n"
        "**Source**: test\n"
        "**Date**: 2026-01-28\n\n"
        "**Pattern**:\nDo the thing well.\n\n"
        "**Evidence**:\n- It worked once\n"
    )

    exp_dir = tmp_path / "experiences" / "content" / "test-project"
    exp_dir.mkdir(parents=True)
    (exp_dir / "plan.md").write_text("# Test Plan")

    return BrainConfig(
        anthropic_api_key="test-key",
        openai_api_key="test-key",
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        brain_data_path=tmp_path,
    )


class TestParsePatterns:
    """Test the pattern parser independently (no external deps)."""

    def test_single_pattern(self):
        migrator = BrainMigrator.__new__(BrainMigrator)
        content = (
            "### Use Exact Words\n\n"
            "**Confidence**: MEDIUM\n"
            "**Source**: LinkedIn session\n"
            "**Date**: 2026-01-24\n\n"
            "**Pattern**:\nUse the user's exact words.\n\n"
            "**Evidence**:\n- Rejected polished versions\n- Accepted raw versions\n"
        )
        patterns = migrator._parse_patterns(content, "test.md")

        assert len(patterns) == 1
        assert patterns[0]["name"] == "Use Exact Words"
        assert patterns[0]["confidence"] == "MEDIUM"
        assert patterns[0]["source_experience"] == "LinkedIn session"
        assert "exact words" in patterns[0]["pattern_text"]
        assert len(patterns[0]["evidence"]) == 2

    def test_multiple_patterns(self):
        migrator = BrainMigrator.__new__(BrainMigrator)
        content = (
            "### Pattern One\n\n"
            "**Confidence**: HIGH\n"
            "**Source**: experience-1\n"
            "**Date**: 2026-01-20\n\n"
            "**Pattern**:\nFirst pattern text.\n\n"
            "**Evidence**:\n- Evidence 1\n\n"
            "### Pattern Two\n\n"
            "**Confidence**: LOW\n"
            "**Source**: experience-2\n"
            "**Date**: 2026-01-22\n\n"
            "**Pattern**:\nSecond pattern text.\n\n"
            "**Evidence**:\n- Evidence 2\n"
        )
        patterns = migrator._parse_patterns(content, "test.md")

        assert len(patterns) == 2
        assert patterns[0]["name"] == "Pattern One"
        assert patterns[1]["name"] == "Pattern Two"

    def test_pattern_with_anti_patterns(self):
        migrator = BrainMigrator.__new__(BrainMigrator)
        content = (
            "### Structured Flow\n\n"
            "**Confidence**: HIGH\n"
            "**Source**: test\n"
            "**Date**: 2026-01-25\n\n"
            "**Pattern**:\nUse structured approach.\n\n"
            "**Evidence**:\n- It works\n\n"
            "**Anti-Pattern**:\n- Don't wing it\n- Don't skip steps\n"
        )
        patterns = migrator._parse_patterns(content, "test.md")

        assert len(patterns) == 1
        assert len(patterns[0]["anti_patterns"]) == 2
        assert "Don't wing it" in patterns[0]["anti_patterns"]

    def test_empty_content(self):
        migrator = BrainMigrator.__new__(BrainMigrator)
        patterns = migrator._parse_patterns("", "test.md")
        assert patterns == []

    def test_no_patterns(self):
        migrator = BrainMigrator.__new__(BrainMigrator)
        content = "# Just a title\n\nSome text without patterns."
        patterns = migrator._parse_patterns(content, "test.md")
        assert patterns == []


class TestBrainMigrator:
    @patch("second_brain.migrate.StorageService")
    @patch("second_brain.migrate.MemoryService")
    async def test_migrate_memory_content(self, mock_mem_cls, mock_storage_cls, mock_config):
        mock_memory = MagicMock()
        mock_memory.add = AsyncMock()
        mock_mem_cls.return_value = mock_memory

        mock_storage = MagicMock()
        mock_storage.upsert_memory_content = AsyncMock(return_value={})
        mock_storage_cls.return_value = mock_storage

        migrator = BrainMigrator(mock_config)
        await migrator.migrate_memory_content()

        # Should have migrated company/products.md
        assert mock_memory.add.call_count >= 1
        assert mock_storage.upsert_memory_content.call_count >= 1

    @patch("second_brain.migrate.StorageService")
    @patch("second_brain.migrate.MemoryService")
    async def test_migrate_patterns(self, mock_mem_cls, mock_storage_cls, mock_config):
        mock_memory = MagicMock()
        mock_memory.add = AsyncMock()
        mock_mem_cls.return_value = mock_memory

        mock_storage = MagicMock()
        mock_storage.upsert_pattern = AsyncMock(return_value={})
        mock_storage_cls.return_value = mock_storage

        migrator = BrainMigrator(mock_config)
        await migrator.migrate_patterns()

        # Should have migrated test-patterns.md (1 pattern), skipped INDEX.md
        assert mock_storage.upsert_pattern.call_count == 1
        assert mock_memory.add.call_count == 1

    @patch("second_brain.migrate.StorageService")
    @patch("second_brain.migrate.MemoryService")
    async def test_migrate_experiences(self, mock_mem_cls, mock_storage_cls, mock_config):
        mock_memory = MagicMock()
        mock_mem_cls.return_value = mock_memory

        mock_storage = MagicMock()
        mock_storage.add_experience = AsyncMock(return_value={})
        mock_storage_cls.return_value = mock_storage

        migrator = BrainMigrator(mock_config)
        await migrator.migrate_experiences()

        # Should have migrated content/test-project
        mock_storage.add_experience.assert_called_once()
        call_args = mock_storage.add_experience.call_args[0][0]
        assert call_args["name"] == "test-project"
        assert call_args["category"] == "content"
        assert "# Test Plan" in call_args["plan_summary"]

    @patch("second_brain.migrate.StorageService")
    @patch("second_brain.migrate.MemoryService")
    async def test_migrate_missing_directories(self, mock_mem_cls, mock_storage_cls, tmp_path):
        """Migration handles missing directories gracefully."""
        config = BrainConfig(
            anthropic_api_key="test-key",
            openai_api_key="test-key",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
            brain_data_path=tmp_path,  # empty dir
        )
        mock_mem_cls.return_value = MagicMock()
        mock_storage_cls.return_value = MagicMock()

        migrator = BrainMigrator(config)
        # Should not raise
        await migrator.migrate_patterns()
        await migrator.migrate_experiences()
