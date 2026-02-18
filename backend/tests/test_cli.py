"""CLI command tests using Click's CliRunner."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from click.testing import CliRunner

from second_brain.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_create_deps():
    """Patch create_deps to return mocked BrainDeps."""
    with patch("second_brain.cli.create_deps") as mock:
        deps = MagicMock()
        deps.config = MagicMock()
        deps.config.graph_provider = "none"
        deps.storage_service = MagicMock()
        deps.storage_service.get_examples = AsyncMock(return_value=[])
        deps.storage_service.get_knowledge = AsyncMock(return_value=[])
        deps.storage_service.delete_pattern = AsyncMock(return_value=True)
        deps.storage_service.delete_experience = AsyncMock(return_value=True)
        deps.storage_service.delete_example = AsyncMock(return_value=True)
        deps.storage_service.delete_knowledge = AsyncMock(return_value=True)
        deps.storage_service.get_content_type_by_slug = AsyncMock(return_value=None)
        deps.storage_service.upsert_content_type = AsyncMock(return_value={"slug": "test"})
        deps.storage_service.delete_content_type = AsyncMock(return_value=True)
        deps.storage_service.get_content_types = AsyncMock(return_value=[])
        # ContentTypeRegistry mock
        registry = MagicMock()
        registry.get = AsyncMock(return_value=None)
        registry.get_all = AsyncMock(return_value={})
        registry.slugs = AsyncMock(return_value=["linkedin", "email"])
        deps.get_content_type_registry = MagicMock(return_value=registry)
        mock.return_value = deps
        yield deps


class TestCLIBasic:
    """Test CLI group and help."""

    def test_cli_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Second Brain" in result.output

    def test_cli_verbose_flag(self, runner):
        result = runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0

    @patch("second_brain.services.health.HealthService")
    def test_subscription_flag_sets_env(self, mock_hs, runner, mock_create_deps, monkeypatch):
        """--subscription flag sets USE_SUBSCRIPTION env var."""
        import os
        monkeypatch.delenv("USE_SUBSCRIPTION", raising=False)
        mock_metrics = MagicMock()
        mock_metrics.memory_count = 0
        mock_metrics.total_patterns = 0
        mock_metrics.high_confidence = 0
        mock_metrics.medium_confidence = 0
        mock_metrics.low_confidence = 0
        mock_metrics.experience_count = 0
        mock_metrics.graph_provider = "none"
        mock_metrics.latest_update = "none"
        mock_metrics.topics = {}
        mock_metrics.status = "BUILDING"
        mock_metrics.graphiti_status = "disabled"
        mock_hs.return_value.compute = AsyncMock(return_value=mock_metrics)
        result = runner.invoke(cli, ["--subscription", "health"])
        assert result.exit_code == 0
        assert os.environ.get("USE_SUBSCRIPTION") == "true"
        # Clean up directly — do NOT use monkeypatch.delenv here because
        # it records "true" as the undo value and restores it on teardown,
        # leaking USE_SUBSCRIPTION=true into subsequent tests.
        os.environ.pop("USE_SUBSCRIPTION", None)


class TestRecallCommand:
    """Test recall command."""

    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.recall.recall_agent")
    def test_recall_success(self, mock_agent, mock_model, runner, mock_create_deps):
        mock_model.return_value = MagicMock()
        mock_output = MagicMock()
        mock_output.query = "test"
        mock_output.matches = []
        mock_output.patterns = []
        mock_output.relations = []
        mock_output.summary = "Test summary"
        mock_agent.run = AsyncMock(return_value=MagicMock(output=mock_output))
        result = runner.invoke(cli, ["recall", "test query"])
        assert result.exit_code == 0
        assert "Recall" in result.output

    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.recall.recall_agent")
    def test_recall_with_populated_output(self, mock_agent, mock_model, runner, mock_create_deps):
        """recall command formats matches, patterns, and relations."""
        mock_model.return_value = MagicMock()
        mock_match = MagicMock()
        mock_match.relevance = "HIGH"
        mock_match.content = "Use compelling hooks"
        mock_match.source = "content-patterns.md"
        mock_relation = MagicMock()
        mock_relation.source = "LinkedIn"
        mock_relation.relationship = "uses"
        mock_relation.target = "hooks"
        mock_output = MagicMock()
        mock_output.query = "hooks"
        mock_output.matches = [mock_match]
        mock_output.patterns = ["Hook First", "Short > Structured"]
        mock_output.relations = [mock_relation]
        mock_output.summary = "Found hook patterns"
        mock_agent.run = AsyncMock(return_value=MagicMock(output=mock_output))
        result = runner.invoke(cli, ["recall", "hooks"])
        assert result.exit_code == 0
        assert "Matches" in result.output
        assert "Use compelling hooks" in result.output
        assert "content-patterns.md" in result.output
        assert "Hook First" in result.output
        assert "Graph Relationships" in result.output
        assert "LinkedIn" in result.output
        assert "uses" in result.output

    def test_recall_missing_query(self, runner):
        result = runner.invoke(cli, ["recall"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output


class TestAskCommand:
    """Test ask command."""

    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.ask.ask_agent")
    def test_ask_success(self, mock_agent, mock_model, runner, mock_create_deps):
        mock_model.return_value = MagicMock()
        mock_output = MagicMock()
        mock_output.answer = "Here is the answer"
        mock_output.context_used = ["patterns"]
        mock_output.patterns_applied = []
        mock_output.relations = []
        mock_output.next_action = None
        mock_agent.run = AsyncMock(return_value=MagicMock(output=mock_output))
        result = runner.invoke(cli, ["ask", "How do I write emails?"])
        assert result.exit_code == 0
        assert "Here is the answer" in result.output

    def test_ask_missing_question(self, runner):
        result = runner.invoke(cli, ["ask"])
        assert result.exit_code != 0


class TestLearnCommand:
    """Test learn command."""

    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.learn.learn_agent")
    def test_learn_success(self, mock_agent, mock_model, runner, mock_create_deps):
        mock_model.return_value = MagicMock()
        mock_output = MagicMock()
        mock_output.input_summary = "Session summary"
        mock_output.patterns_extracted = []
        mock_output.insights = ["Key insight"]
        mock_output.experience_recorded = True
        mock_output.experience_category = "content"
        mock_output.patterns_new = 1
        mock_output.patterns_reinforced = 0
        mock_output.storage_summary = "1 pattern stored"
        mock_agent.run = AsyncMock(return_value=MagicMock(output=mock_output))
        result = runner.invoke(cli, ["learn", "Today I learned about hooks"])
        assert result.exit_code == 0
        assert "Learn" in result.output

    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.learn.learn_agent")
    def test_learn_with_patterns_output(self, mock_agent, mock_model, runner, mock_create_deps):
        """learn command formats extracted patterns with details."""
        mock_model.return_value = MagicMock()
        mock_pattern = MagicMock()
        mock_pattern.confidence = "MEDIUM"
        mock_pattern.name = "Hook First"
        mock_pattern.is_reinforcement = False
        mock_pattern.pattern_text = "Always start with a compelling hook that grabs attention"
        mock_pattern.anti_patterns = ["Starting with a question", "Generic openings"]
        mock_output = MagicMock()
        mock_output.input_summary = "Content writing session"
        mock_output.patterns_extracted = [mock_pattern]
        mock_output.insights = ["Hooks outperform questions"]
        mock_output.experience_recorded = True
        mock_output.experience_category = "content"
        mock_output.patterns_new = 1
        mock_output.patterns_reinforced = 0
        mock_output.storage_summary = "1 pattern stored"
        mock_agent.run = AsyncMock(return_value=MagicMock(output=mock_output))
        result = runner.invoke(cli, ["learn", "Today I learned about hooks"])
        assert result.exit_code == 0
        assert "Hook First" in result.output
        assert "(new)" in result.output
        assert "MEDIUM" in result.output
        assert "Anti:" in result.output
        assert "Starting with a question" in result.output
        assert "Insights" in result.output

    def test_learn_missing_content(self, runner):
        result = runner.invoke(cli, ["learn"])
        assert result.exit_code != 0


class TestCreateCommand:
    """Test create command."""

    @patch("second_brain.cli.get_model")
    def test_create_unknown_type(self, mock_model, runner, mock_create_deps):
        mock_model.return_value = MagicMock()
        # registry.get returns None for unknown type
        result = runner.invoke(cli, ["create", "Write a post", "--type", "unknown"])
        assert result.exit_code == 0
        assert "Unknown content type" in result.output

    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.create.create_agent")
    def test_create_success(self, mock_agent, mock_model, runner, mock_create_deps):
        mock_model.return_value = MagicMock()
        # Set up registry to return a valid type config
        type_config = MagicMock()
        type_config.name = "LinkedIn Post"
        type_config.default_mode = "casual"
        type_config.structure_hint = "Hook -> Body -> CTA"
        type_config.max_words = 300
        registry = mock_create_deps.get_content_type_registry()
        registry.get = AsyncMock(return_value=type_config)

        mock_output = MagicMock()
        mock_output.content_type = "linkedin"
        mock_output.mode = "casual"
        mock_output.draft = "Check out our new product..."
        mock_output.word_count = 85
        mock_output.voice_elements = ["direct"]
        mock_output.patterns_applied = []
        mock_output.examples_referenced = []
        mock_output.notes = None
        mock_agent.run = AsyncMock(return_value=MagicMock(output=mock_output))
        result = runner.invoke(cli, ["create", "Write about AI"])
        assert result.exit_code == 0
        assert "Draft" in result.output

    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.create.create_agent")
    def test_create_with_mode_override(self, mock_agent, mock_model, runner, mock_create_deps):
        """create command passes --mode override to agent prompt."""
        mock_model.return_value = MagicMock()
        type_config = MagicMock()
        type_config.name = "LinkedIn Post"
        type_config.default_mode = "casual"
        type_config.structure_hint = "Hook -> Body -> CTA"
        type_config.max_words = 300
        registry = mock_create_deps.get_content_type_registry()
        registry.get = AsyncMock(return_value=type_config)
        mock_output = MagicMock()
        mock_output.content_type = "linkedin"
        mock_output.mode = "formal"
        mock_output.draft = "Draft content here"
        mock_output.word_count = 80
        mock_output.voice_elements = []
        mock_output.patterns_applied = []
        mock_output.examples_referenced = []
        mock_output.notes = None
        mock_agent.run = AsyncMock(return_value=MagicMock(output=mock_output))
        result = runner.invoke(cli, ["create", "Write about AI", "--mode", "formal"])
        assert result.exit_code == 0
        call_args = mock_agent.run.call_args
        prompt = call_args[0][0]
        assert "Communication mode: formal" in prompt


class TestReviewCommand:
    """Test review command."""

    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.review.run_full_review")
    def test_review_success(self, mock_review, mock_model, runner, mock_create_deps):
        mock_model.return_value = MagicMock()
        mock_result = MagicMock()
        mock_result.overall_score = 8.0
        mock_result.verdict = "READY TO SEND"
        mock_result.summary = "Good content"
        mock_result.scores = []
        mock_result.top_strengths = ["Clear"]
        mock_result.critical_issues = []
        mock_result.next_steps = []
        mock_review.return_value = mock_result
        result = runner.invoke(cli, ["review", "Test content"])
        assert result.exit_code == 0
        assert "Review" in result.output

    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.review.run_full_review")
    def test_review_with_type_flag(self, mock_review, mock_model, runner, mock_create_deps):
        """review command passes --type flag to run_full_review."""
        mock_model.return_value = MagicMock()
        mock_result = MagicMock()
        mock_result.overall_score = 7.5
        mock_result.verdict = "NEEDS REVISION"
        mock_result.summary = "Good but needs work"
        mock_result.scores = []
        mock_result.top_strengths = []
        mock_result.critical_issues = []
        mock_result.next_steps = []
        mock_review.return_value = mock_result
        result = runner.invoke(cli, ["review", "Test content", "--type", "email"])
        assert result.exit_code == 0
        mock_review.assert_called_once()
        call_args = mock_review.call_args[0]
        assert call_args[3] == "email"


class TestExamplesCommand:
    """Test examples command."""

    def test_examples_empty(self, runner, mock_create_deps):
        result = runner.invoke(cli, ["examples"])
        assert result.exit_code == 0
        assert "No content examples found" in result.output

    def test_examples_with_results(self, runner, mock_create_deps):
        mock_create_deps.storage_service.get_examples = AsyncMock(return_value=[
            {"content_type": "linkedin", "title": "Good Hook", "content": "Start with..."},
        ])
        result = runner.invoke(cli, ["examples"])
        assert result.exit_code == 0
        assert "linkedin" in result.output

    def test_examples_with_type_filter(self, runner, mock_create_deps):
        result = runner.invoke(cli, ["examples", "--type", "email"])
        assert result.exit_code == 0


class TestKnowledgeCommand:
    """Test knowledge command."""

    def test_knowledge_empty(self, runner, mock_create_deps):
        result = runner.invoke(cli, ["knowledge"])
        assert result.exit_code == 0
        assert "No knowledge entries found" in result.output

    def test_knowledge_with_results(self, runner, mock_create_deps):
        mock_create_deps.storage_service.get_knowledge = AsyncMock(return_value=[
            {"category": "frameworks", "title": "Value Ladder", "content": "Framework..."},
        ])
        result = runner.invoke(cli, ["knowledge"])
        assert result.exit_code == 0
        assert "frameworks" in result.output


class TestDeleteCommand:
    """Test delete command."""

    def test_delete_success(self, runner, mock_create_deps):
        result = runner.invoke(cli, ["delete", "pattern", "uuid-123"])
        assert result.exit_code == 0
        assert "Deleted pattern" in result.output

    def test_delete_not_found(self, runner, mock_create_deps):
        mock_create_deps.storage_service.delete_pattern = AsyncMock(return_value=False)
        result = runner.invoke(cli, ["delete", "pattern", "nonexistent"])
        assert result.exit_code == 0
        assert "No pattern found" in result.output

    def test_delete_invalid_table(self, runner, mock_create_deps):
        result = runner.invoke(cli, ["delete", "invalid", "uuid-123"])
        assert result.exit_code != 0


class TestHealthCommand:
    """Test health command."""

    @patch("second_brain.services.health.HealthService")
    def test_health_success(self, mock_hs, runner, mock_create_deps):
        mock_metrics = MagicMock()
        mock_metrics.memory_count = 42
        mock_metrics.total_patterns = 5
        mock_metrics.high_confidence = 2
        mock_metrics.medium_confidence = 2
        mock_metrics.low_confidence = 1
        mock_metrics.experience_count = 3
        mock_metrics.graph_provider = "none"
        mock_metrics.latest_update = "2026-02-15"
        mock_metrics.topics = {"content": 3}
        mock_metrics.status = "BUILDING"
        mock_hs.return_value.compute = AsyncMock(return_value=mock_metrics)
        result = runner.invoke(cli, ["health"])
        assert result.exit_code == 0
        assert "Memories: 42" in result.output
        assert "Patterns: 5" in result.output

    @patch("second_brain.services.health.HealthService")
    def test_health_with_graphiti_enabled(self, mock_hs, runner, mock_create_deps):
        """health command shows Graphiti status when not disabled."""
        mock_metrics = MagicMock()
        mock_metrics.memory_count = 42
        mock_metrics.total_patterns = 5
        mock_metrics.high_confidence = 2
        mock_metrics.medium_confidence = 2
        mock_metrics.low_confidence = 1
        mock_metrics.experience_count = 3
        mock_metrics.graph_provider = "none"
        mock_metrics.latest_update = "2026-02-15"
        mock_metrics.topics = {}
        mock_metrics.status = "BUILDING"
        mock_metrics.graphiti_status = "healthy"
        mock_metrics.graphiti_backend = "neo4j"
        mock_hs.return_value.compute = AsyncMock(return_value=mock_metrics)
        result = runner.invoke(cli, ["health"])
        assert result.exit_code == 0
        assert "Graphiti: healthy" in result.output
        assert "neo4j" in result.output

    @patch("second_brain.services.health.HealthService")
    def test_health_no_topics(self, mock_hs, runner, mock_create_deps):
        """health command skips topics section when topics is empty."""
        mock_metrics = MagicMock()
        mock_metrics.memory_count = 10
        mock_metrics.total_patterns = 2
        mock_metrics.high_confidence = 1
        mock_metrics.medium_confidence = 1
        mock_metrics.low_confidence = 0
        mock_metrics.experience_count = 1
        mock_metrics.graph_provider = "none"
        mock_metrics.latest_update = "2026-02-15"
        mock_metrics.topics = {}
        mock_metrics.status = "BUILDING"
        mock_metrics.graphiti_status = "disabled"
        mock_hs.return_value.compute = AsyncMock(return_value=mock_metrics)
        result = runner.invoke(cli, ["health"])
        assert result.exit_code == 0
        assert "Patterns by Topic" not in result.output


class TestGrowthCommand:
    """Test growth command."""

    @patch("second_brain.services.health.HealthService")
    def test_growth_success(self, mock_hs, runner, mock_create_deps):
        mock_metrics = MagicMock()
        mock_metrics.status = "GROWING"
        mock_metrics.total_patterns = 10
        mock_metrics.high_confidence = 3
        mock_metrics.medium_confidence = 5
        mock_metrics.low_confidence = 2
        mock_metrics.growth_events_total = 15
        mock_metrics.patterns_created_period = 5
        mock_metrics.patterns_reinforced_period = 8
        mock_metrics.confidence_upgrades_period = 2
        mock_metrics.reviews_completed_period = 0
        mock_metrics.stale_patterns = []
        mock_metrics.topics = {}
        mock_hs.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
        result = runner.invoke(cli, ["growth"])
        assert result.exit_code == 0
        assert "Growth Report" in result.output
        assert "GROWING" in result.output

    @patch("second_brain.services.health.HealthService")
    def test_growth_with_reviews(self, mock_hs, runner, mock_create_deps):
        """growth command shows quality metrics when reviews exist."""
        mock_metrics = MagicMock()
        mock_metrics.status = "GROWING"
        mock_metrics.graphiti_status = "disabled"
        mock_metrics.total_patterns = 10
        mock_metrics.high_confidence = 3
        mock_metrics.medium_confidence = 5
        mock_metrics.low_confidence = 2
        mock_metrics.growth_events_total = 15
        mock_metrics.patterns_created_period = 5
        mock_metrics.patterns_reinforced_period = 8
        mock_metrics.confidence_upgrades_period = 2
        mock_metrics.reviews_completed_period = 4
        mock_metrics.avg_review_score = 8.2
        mock_metrics.review_score_trend = "improving"
        mock_metrics.stale_patterns = []
        mock_metrics.topics = {}
        mock_hs.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
        result = runner.invoke(cli, ["growth"])
        assert result.exit_code == 0
        assert "Quality Metrics" in result.output
        assert "8.2" in result.output
        assert "improving" in result.output

    @patch("second_brain.services.health.HealthService")
    def test_growth_with_stale_patterns(self, mock_hs, runner, mock_create_deps):
        """growth command shows stale patterns when present."""
        mock_metrics = MagicMock()
        mock_metrics.status = "GROWING"
        mock_metrics.graphiti_status = "disabled"
        mock_metrics.total_patterns = 10
        mock_metrics.high_confidence = 3
        mock_metrics.medium_confidence = 5
        mock_metrics.low_confidence = 2
        mock_metrics.growth_events_total = 15
        mock_metrics.patterns_created_period = 5
        mock_metrics.patterns_reinforced_period = 8
        mock_metrics.confidence_upgrades_period = 2
        mock_metrics.reviews_completed_period = 0
        mock_metrics.stale_patterns = ["Old Pattern", "Forgotten Rule"]
        mock_metrics.topics = {}
        mock_hs.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
        result = runner.invoke(cli, ["growth"])
        assert result.exit_code == 0
        assert "Stale Patterns" in result.output
        assert "Old Pattern" in result.output

    @patch("second_brain.services.health.HealthService")
    def test_growth_custom_days(self, mock_hs, runner, mock_create_deps):
        """growth command accepts --days option."""
        mock_metrics = MagicMock()
        mock_metrics.status = "BUILDING"
        mock_metrics.graphiti_status = "disabled"
        mock_metrics.total_patterns = 5
        mock_metrics.high_confidence = 1
        mock_metrics.medium_confidence = 2
        mock_metrics.low_confidence = 2
        mock_metrics.growth_events_total = 3
        mock_metrics.patterns_created_period = 2
        mock_metrics.patterns_reinforced_period = 1
        mock_metrics.confidence_upgrades_period = 0
        mock_metrics.reviews_completed_period = 0
        mock_metrics.stale_patterns = []
        mock_metrics.topics = {}
        mock_hs.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
        result = runner.invoke(cli, ["growth", "--days", "7"])
        assert result.exit_code == 0
        assert "Growth Report (7 days)" in result.output

    @patch("second_brain.services.health.HealthService")
    def test_growth_with_topics(self, mock_hs, runner, mock_create_deps):
        """growth command shows topics breakdown."""
        mock_metrics = MagicMock()
        mock_metrics.status = "GROWING"
        mock_metrics.graphiti_status = "disabled"
        mock_metrics.total_patterns = 10
        mock_metrics.high_confidence = 3
        mock_metrics.medium_confidence = 5
        mock_metrics.low_confidence = 2
        mock_metrics.growth_events_total = 15
        mock_metrics.patterns_created_period = 5
        mock_metrics.patterns_reinforced_period = 8
        mock_metrics.confidence_upgrades_period = 2
        mock_metrics.reviews_completed_period = 0
        mock_metrics.stale_patterns = []
        mock_metrics.topics = {"content": 5, "messaging": 3}
        mock_hs.return_value.compute_growth = AsyncMock(return_value=mock_metrics)
        result = runner.invoke(cli, ["growth"])
        assert result.exit_code == 0
        assert "content: 5" in result.output
        assert "messaging: 3" in result.output


class TestConsolidateCommand:
    """Test consolidate command."""

    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.learn.learn_agent")
    def test_consolidate_success(self, mock_agent, mock_model, runner, mock_create_deps):
        mock_model.return_value = MagicMock()
        mock_output = MagicMock()
        mock_output.input_summary = "Reviewed 10 memories"
        mock_output.patterns_extracted = []
        mock_output.patterns_new = 2
        mock_output.patterns_reinforced = 1
        mock_agent.run = AsyncMock(return_value=MagicMock(output=mock_output))
        result = runner.invoke(cli, ["consolidate"])
        assert result.exit_code == 0
        assert "Consolidation" in result.output
        assert "2 new" in result.output


class TestTypesListCommand:
    """Test types list command."""

    def test_types_list_empty(self, runner, mock_create_deps):
        result = runner.invoke(cli, ["types", "list"])
        assert result.exit_code == 0
        assert "No content types found" in result.output

    def test_types_list_with_results(self, runner, mock_create_deps):
        type_config = MagicMock()
        type_config.name = "LinkedIn Post"
        type_config.default_mode = "casual"
        type_config.max_words = 300
        type_config.is_builtin = True
        type_config.review_dimensions = None
        registry = mock_create_deps.get_content_type_registry()
        registry.get_all = AsyncMock(return_value={"linkedin": type_config})
        result = runner.invoke(cli, ["types", "list"])
        assert result.exit_code == 0
        assert "linkedin" in result.output
        assert "LinkedIn Post" in result.output


class TestTypesAddCommand:
    """Test types add command."""

    def test_types_add_success(self, runner, mock_create_deps):
        result = runner.invoke(cli, [
            "types", "add", "newsletter", "Newsletter",
            "--structure", "Intro -> Body -> CTA",
        ])
        assert result.exit_code == 0
        assert "Added content type" in result.output

    def test_types_add_missing_structure(self, runner, mock_create_deps):
        result = runner.invoke(cli, ["types", "add", "newsletter", "Newsletter"])
        assert result.exit_code != 0


class TestTypesRemoveCommand:
    """Test types remove command."""

    def test_types_remove_not_found(self, runner, mock_create_deps):
        result = runner.invoke(cli, ["types", "remove", "nonexistent"])
        assert result.exit_code == 0
        assert "No content type found" in result.output

    def test_types_remove_builtin_blocked(self, runner, mock_create_deps):
        mock_create_deps.storage_service.get_content_type_by_slug = AsyncMock(
            return_value={"slug": "linkedin", "is_builtin": True}
        )
        result = runner.invoke(cli, ["types", "remove", "linkedin"])
        assert result.exit_code == 0
        assert "built-in" in result.output

    def test_types_remove_builtin_force(self, runner, mock_create_deps):
        mock_create_deps.storage_service.get_content_type_by_slug = AsyncMock(
            return_value={"slug": "linkedin", "is_builtin": True}
        )
        result = runner.invoke(cli, ["types", "remove", "linkedin", "--force"])
        assert result.exit_code == 0
        assert "Removed" in result.output


class TestCLIAgentErrors:
    """Tests for CLI behavior when agents raise exceptions."""

    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.recall.recall_agent")
    def test_recall_agent_error(self, mock_agent, mock_model, runner, mock_create_deps):
        """CLI shows traceback/error when recall agent fails."""
        mock_model.return_value = MagicMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("LLM timeout"))
        result = runner.invoke(cli, ["recall", "test query"])
        assert result.exit_code != 0

    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.ask.ask_agent")
    def test_ask_agent_error(self, mock_agent, mock_model, runner, mock_create_deps):
        """CLI shows traceback/error when ask agent fails."""
        mock_model.return_value = MagicMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("Service unavailable"))
        result = runner.invoke(cli, ["ask", "test question"])
        assert result.exit_code != 0

    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.create.create_agent")
    def test_create_agent_error(self, mock_agent, mock_model, runner, mock_create_deps):
        """CLI shows traceback/error when create agent fails."""
        mock_model.return_value = MagicMock()
        # Set up registry to return a valid type config
        type_config = MagicMock()
        type_config.name = "LinkedIn Post"
        type_config.default_mode = "casual"
        type_config.structure_hint = "Hook -> Body -> CTA"
        type_config.max_words = 300
        registry = mock_create_deps.get_content_type_registry()
        registry.get = AsyncMock(return_value=type_config)
        mock_agent.run = AsyncMock(side_effect=RuntimeError("Model unavailable"))
        result = runner.invoke(cli, ["create", "test", "--type", "linkedin"])
        assert result.exit_code != 0

    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.review.run_full_review")
    def test_review_agent_error(self, mock_review, mock_model, runner, mock_create_deps):
        """CLI shows traceback/error when review fails."""
        mock_model.return_value = MagicMock()
        mock_review.side_effect = RuntimeError("Review failed")
        result = runner.invoke(cli, ["review", "Test content"])
        assert result.exit_code != 0

    @patch("second_brain.cli.get_model")
    @patch("second_brain.agents.learn.learn_agent")
    def test_learn_agent_error(self, mock_agent, mock_model, runner, mock_create_deps):
        """CLI shows traceback/error when learn agent fails."""
        mock_model.return_value = MagicMock()
        mock_agent.run = AsyncMock(side_effect=RuntimeError("Learn failed"))
        result = runner.invoke(cli, ["learn", "test content"])
        assert result.exit_code != 0


class TestCLIInputValidation:
    """Test input validation on CLI commands."""

    def test_recall_empty_string_rejected(self, runner, mock_create_deps):
        result = runner.invoke(cli, ["recall", ""])
        assert result.exit_code != 0 or "empty" in result.output.lower()

    def test_recall_very_long_input_rejected(self, runner, mock_create_deps):
        long_query = "x" * 15000
        result = runner.invoke(cli, ["recall", long_query])
        assert result.exit_code != 0 or "too long" in result.output.lower()

    def test_ask_whitespace_only_rejected(self, runner, mock_create_deps):
        result = runner.invoke(cli, ["ask", "   "])
        assert result.exit_code != 0 or "empty" in result.output.lower()

    def test_learn_empty_content_rejected(self, runner, mock_create_deps):
        result = runner.invoke(cli, ["learn", ""])
        assert result.exit_code != 0 or "empty" in result.output.lower()

    def test_create_empty_prompt_rejected(self, runner, mock_create_deps):
        result = runner.invoke(cli, ["create", ""])
        assert result.exit_code != 0 or "empty" in result.output.lower()

    def test_review_whitespace_only_rejected(self, runner, mock_create_deps):
        result = runner.invoke(cli, ["review", "   "])
        assert result.exit_code != 0 or "empty" in result.output.lower()

    def test_delete_long_id_rejected(self, runner, mock_create_deps):
        long_id = "x" * 200
        result = runner.invoke(cli, ["delete", "pattern", long_id])
        assert result.exit_code != 0 or "too long" in result.output.lower()

    def test_delete_empty_id_rejected(self, runner, mock_create_deps):
        result = runner.invoke(cli, ["delete", "pattern", ""])
        assert result.exit_code != 0 or "empty" in result.output.lower()


class TestCLIGraph:
    """Test graph subcommand group."""

    def test_graph_health_not_enabled(self, runner, mock_create_deps):
        """graph health when Graphiti is not enabled."""
        mock_create_deps.graphiti_service = None
        result = runner.invoke(cli, ["graph", "health"])
        assert "not enabled" in result.output.lower()

    def test_graph_health_enabled(self, runner, mock_create_deps):
        """graph health when Graphiti is healthy."""
        mock_graphiti = AsyncMock()
        mock_graphiti.health_check = AsyncMock(return_value={
            "status": "healthy",
            "backend": "neo4j",
        })
        mock_create_deps.graphiti_service = mock_graphiti
        result = runner.invoke(cli, ["graph", "health"])
        assert "healthy" in result.output
        assert "neo4j" in result.output

    def test_graph_search_no_results(self, runner, mock_create_deps):
        """graph search with no results."""
        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        mock_create_deps.graphiti_service = mock_graphiti
        result = runner.invoke(cli, ["graph", "search", "test query"])
        assert "not enabled" in result.output.lower() or "no graph relationships" in result.output.lower()

    def test_graph_search_with_results(self, runner, mock_create_deps):
        """graph search returning relationships."""
        mock_graphiti = AsyncMock()
        mock_graphiti.search = AsyncMock(return_value=[
            {"source": "Alice", "relationship": "works_with", "target": "Bob"},
        ])
        mock_create_deps.graphiti_service = mock_graphiti
        result = runner.invoke(cli, ["graph", "search", "team members"])
        assert "Alice" in result.output
        assert "works_with" in result.output
        assert "Bob" in result.output


class TestProjectCLI:
    """Test project lifecycle CLI commands."""

    def test_project_create(self, runner, mock_create_deps):
        mock_create_deps.storage_service.create_project = AsyncMock(
            return_value={"id": "proj-1", "name": "Test Project"}
        )
        result = runner.invoke(cli, ["project", "create", "Test Project"])
        assert result.exit_code == 0
        assert "Project created" in result.output
        assert "Test Project" in result.output

    def test_project_create_failure(self, runner, mock_create_deps):
        mock_create_deps.storage_service.create_project = AsyncMock(return_value=None)
        result = runner.invoke(cli, ["project", "create", "Fail"])
        assert "Failed" in result.output

    def test_project_list(self, runner, mock_create_deps):
        mock_create_deps.storage_service.list_projects = AsyncMock(return_value=[
            {"id": "p1", "name": "Alpha", "lifecycle_stage": "planning"},
            {"id": "p2", "name": "Beta", "lifecycle_stage": "complete"},
        ])
        result = runner.invoke(cli, ["project", "list"])
        assert result.exit_code == 0
        assert "Alpha" in result.output
        assert "Beta" in result.output

    def test_project_list_empty(self, runner, mock_create_deps):
        mock_create_deps.storage_service.list_projects = AsyncMock(return_value=[])
        result = runner.invoke(cli, ["project", "list"])
        assert "No projects found" in result.output

    def test_project_status(self, runner, mock_create_deps):
        mock_create_deps.storage_service.get_project = AsyncMock(return_value={
            "name": "My Project", "lifecycle_stage": "executing",
            "category": "content", "project_artifacts": [],
        })
        result = runner.invoke(cli, ["project", "status", "proj-1"])
        assert result.exit_code == 0
        assert "My Project" in result.output
        assert "executing" in result.output

    def test_project_status_not_found(self, runner, mock_create_deps):
        mock_create_deps.storage_service.get_project = AsyncMock(return_value=None)
        result = runner.invoke(cli, ["project", "status", "missing"])
        assert "not found" in result.output.lower()

    @patch("second_brain.services.health.HealthService")
    def test_setup_command(self, mock_hs, runner, mock_create_deps):
        mock_instance = MagicMock()
        mock_instance.compute_setup_status = AsyncMock(return_value={
            "completed_count": 5, "total_steps": 8, "is_complete": False,
            "missing_categories": ["voice_guide"],
            "steps": [
                {"description": "Patterns loaded", "completed": True},
                {"description": "Voice guide", "completed": False},
            ],
        })
        mock_hs.return_value = mock_instance
        result = runner.invoke(cli, ["setup"])
        assert result.exit_code == 0
        assert "Brain Setup" in result.output
        assert "[x]" in result.output
        assert "[ ]" in result.output

    @patch("second_brain.agents.utils.format_pattern_registry")
    def test_patterns_command(self, mock_format, runner, mock_create_deps):
        mock_create_deps.storage_service.get_pattern_registry = AsyncMock(return_value=[
            {"name": "Hook", "confidence": "HIGH"},
        ])
        mock_format.return_value = "| Hook | HIGH |"
        result = runner.invoke(cli, ["patterns"])
        assert result.exit_code == 0
        assert "Pattern Registry" in result.output


class TestMigrateCommand:
    """Test migrate command."""

    @patch("second_brain.migrate.run_migration")
    def test_migrate_success(self, mock_migrate, runner, mock_create_deps):
        mock_migrate.return_value = None
        result = runner.invoke(cli, ["migrate"])
        assert result.exit_code == 0
        assert "Migration complete" in result.output
