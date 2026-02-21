"""Consolidated tests for recall_agent — semantic memory search.

This file consolidates tests from:
- test_agents.py::TestRecallAgent*
- test_agents.py::TestRecallValidatorResilience
- test_agents.py::TestParallelSearchSemanticMemory
- test_agentic.py::TestRecallValidator

Focus areas:
1. Death spiral prevention (all backends fail)
2. Deterministic error detection
3. Graceful degradation on partial failures
4. Search source tracking
"""

from unittest.mock import MagicMock

import pytest
from pydantic_ai import ModelRetry

from second_brain.agents.recall import recall_agent, validate_recall
from second_brain.agents.utils import TOOL_ERROR_PREFIX, all_tools_failed, any_tool_failed
from second_brain.deps import BrainDeps
from second_brain.schemas import MemoryMatch, RecallResult, Relation


class TestToolErrorHelpers:
    """Test the deterministic error detection helpers."""

    def test_all_tools_failed_empty_list(self):
        """Empty list returns False (no tools called)."""
        assert all_tools_failed([]) is False

    def test_all_tools_failed_all_errors(self):
        """Returns True when all outputs are errors."""
        outputs = [
            f"{TOOL_ERROR_PREFIX} tool1: ConnectionError",
            f"{TOOL_ERROR_PREFIX} tool2: TimeoutError",
        ]
        assert all_tools_failed(outputs) is True

    def test_all_tools_failed_mixed(self):
        """Returns False when some outputs are successful."""
        outputs = [
            f"{TOOL_ERROR_PREFIX} tool1: ConnectionError",
            "Some successful results here",
        ]
        assert all_tools_failed(outputs) is False

    def test_all_tools_failed_all_success(self):
        """Returns False when all outputs are successful."""
        outputs = [
            "Found 5 memories",
            "Pattern match: XYZ",
        ]
        assert all_tools_failed(outputs) is False

    def test_all_tools_failed_handles_non_string(self):
        """Returns False when outputs contain non-strings."""
        outputs = [
            f"{TOOL_ERROR_PREFIX} tool1: error",
            123,  # non-string
        ]
        assert all_tools_failed(outputs) is False

    def test_any_tool_failed_detects_single_error(self):
        """Returns True when any output is an error."""
        outputs = [
            "Success",
            f"{TOOL_ERROR_PREFIX} tool2: error",
        ]
        assert any_tool_failed(outputs) is True

    def test_any_tool_failed_no_errors(self):
        """Returns False when no errors present."""
        outputs = ["Success1", "Success2"]
        assert any_tool_failed(outputs) is False

    def test_any_tool_failed_empty_list(self):
        """Empty list returns False."""
        assert any_tool_failed([]) is False


class TestRecallValidatorResilience:
    """Test validator handles backend failures gracefully."""

    @pytest.fixture
    def mock_ctx(self):
        ctx = MagicMock()
        ctx.deps = MagicMock(spec=BrainDeps)
        ctx.messages = []
        return ctx

    async def test_accepts_output_with_error_field(self, mock_ctx):
        """Validator accepts output when error field is set."""
        output = RecallResult(
            query="test",
            matches=[],
            patterns=[],
            relations=[],
            search_sources=[],
            error="All backends unavailable",
        )
        result = await validate_recall(mock_ctx, output)
        assert result.error == "All backends unavailable"

    async def test_accepts_empty_results_with_search_sources(self, mock_ctx):
        """Validator accepts empty results if search was attempted."""
        output = RecallResult(
            query="test",
            matches=[],
            patterns=[],
            relations=[],
            search_sources=["mem0", "pgvector:patterns"],
            error="",
        )
        result = await validate_recall(mock_ctx, output)
        assert result == output

    async def test_retries_when_no_search_attempted(self, mock_ctx):
        """Validator raises ModelRetry when no search sources recorded."""
        output = RecallResult(
            query="test",
            matches=[],
            patterns=[],
            relations=[],
            search_sources=[],
            error="",
        )
        with pytest.raises(ModelRetry):
            await validate_recall(mock_ctx, output)

    async def test_accepts_partial_results(self, mock_ctx):
        """Validator accepts output with any results."""
        output = RecallResult(
            query="test",
            matches=[],
            patterns=["pattern1"],
            relations=[],
            search_sources=["mem0"],
            error="",
        )
        result = await validate_recall(mock_ctx, output)
        assert result.patterns == ["pattern1"]

    async def test_accepts_results_with_matches(self, mock_ctx):
        """Validator accepts output with matches."""
        output = RecallResult(
            query="test",
            matches=[MemoryMatch(content="match1", score=0.9, source="mem0")],
            patterns=[],
            relations=[],
            search_sources=["hybrid"],
            error="",
        )
        result = await validate_recall(mock_ctx, output)
        assert len(result.matches) == 1

    async def test_accepts_results_with_relations(self, mock_ctx):
        """Validator accepts output with relations."""
        output = RecallResult(
            query="test",
            matches=[],
            patterns=[],
            relations=[Relation(source="A", relationship="relates_to", target="B")],
            search_sources=["graphiti"],
            error="",
        )
        result = await validate_recall(mock_ctx, output)
        assert len(result.relations) == 1


class TestRecallValidatorDeterministicError:
    """Test deterministic error detection in validator."""

    @pytest.fixture
    def mock_ctx_with_errors(self):
        """Context with tool messages that are all errors."""
        ctx = MagicMock()
        ctx.deps = MagicMock(spec=BrainDeps)

        # Simulate tool result messages
        msg1 = MagicMock()
        part1 = MagicMock()
        part1.content = f"{TOOL_ERROR_PREFIX} search_semantic_memory: ConnectionError"
        msg1.parts = [part1]

        msg2 = MagicMock()
        part2 = MagicMock()
        part2.content = f"{TOOL_ERROR_PREFIX} search_patterns: TimeoutError"
        msg2.parts = [part2]

        ctx.messages = [msg1, msg2]
        return ctx

    @pytest.fixture
    def mock_ctx_with_mixed(self):
        """Context with mixed success and error messages."""
        ctx = MagicMock()
        ctx.deps = MagicMock(spec=BrainDeps)

        msg1 = MagicMock()
        part1 = MagicMock()
        part1.content = f"{TOOL_ERROR_PREFIX} search_semantic_memory: error"
        msg1.parts = [part1]

        msg2 = MagicMock()
        part2 = MagicMock()
        part2.content = "Found 3 memories matching query"
        msg2.parts = [part2]

        ctx.messages = [msg1, msg2]
        return ctx

    async def test_sets_error_when_all_tools_failed(self, mock_ctx_with_errors):
        """Validator sets error field when all tool outputs are errors."""
        output = RecallResult(
            query="test",
            matches=[],
            patterns=[],
            relations=[],
            search_sources=[],
            error="",
        )
        result = await validate_recall(mock_ctx_with_errors, output)

        assert result.error == "All search backends unavailable. Memory search skipped."
        assert "error:all_backends_failed" in result.search_sources

    async def test_allows_retry_when_partial_success(self, mock_ctx_with_mixed):
        """Validator allows retry when some tools succeeded."""
        output = RecallResult(
            query="test",
            matches=[],
            patterns=[],
            relations=[],
            search_sources=[],
            error="",
        )
        # Should raise ModelRetry since no search_sources and not all failed
        with pytest.raises(ModelRetry):
            await validate_recall(mock_ctx_with_mixed, output)


class TestRecallAgentConfiguration:
    """Test agent configuration."""

    def test_retries_is_two(self):
        """recall_agent retries should be 2 (reduced from 3)."""
        assert recall_agent._max_result_retries == 2

    def test_has_output_validator(self):
        """recall_agent should have output validator."""
        assert recall_agent._output_validators is not None
        assert len(recall_agent._output_validators) > 0

    def test_has_search_tools(self):
        """recall_agent should have all search tools."""
        tool_names = list(recall_agent._function_toolset.tools)
        assert "search_semantic_memory" in tool_names
        assert "search_patterns" in tool_names
        assert "search_experiences" in tool_names
        assert "search_examples" in tool_names
        assert "search_projects" in tool_names

    def test_has_deps_type(self):
        """recall_agent should have BrainDeps as deps_type."""
        assert recall_agent._deps_type == BrainDeps


class TestRecallResultSchema:
    """Test RecallResult schema."""

    def test_error_field_default_empty(self):
        """error field defaults to empty string."""
        result = RecallResult(query="test")
        assert result.error == ""

    def test_search_sources_default_empty(self):
        """search_sources defaults to empty list."""
        result = RecallResult(query="test")
        assert result.search_sources == []

    def test_accepts_error_with_empty_results(self):
        """Schema accepts error field with no other results."""
        result = RecallResult(
            query="test",
            error="Backend failure",
        )
        assert result.error == "Backend failure"
        assert result.matches == []

    def test_model_copy_preserves_fields(self):
        """model_copy(update={...}) works as expected."""
        match = MemoryMatch(content="m1", score=0.9, source="test")
        original = RecallResult(query="test", matches=[match])
        updated = original.model_copy(update={"error": "new error"})

        assert updated.error == "new error"
        assert len(updated.matches) == 1
        assert updated.matches[0].content == "m1"
        assert updated.query == "test"

    def test_default_values(self):
        """All fields have sensible defaults."""
        result = RecallResult(query="test")
        assert result.matches == []
        assert result.patterns == []
        assert result.relations == []
        assert result.search_sources == []
        assert result.error == ""


class TestToolErrorPrefix:
    """Test TOOL_ERROR_PREFIX constant."""

    def test_prefix_value(self):
        """TOOL_ERROR_PREFIX should be BACKEND_ERROR:"""
        assert TOOL_ERROR_PREFIX == "BACKEND_ERROR:"

    def test_prefix_used_in_tool_error(self):
        """tool_error() returns string starting with prefix."""
        from second_brain.agents.utils import tool_error

        result = tool_error("test_tool", ValueError("test"))
        assert result.startswith(TOOL_ERROR_PREFIX)
        assert "test_tool" in result
