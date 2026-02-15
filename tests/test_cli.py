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


class TestMigrateCommand:
    """Test migrate command."""

    @patch("second_brain.migrate.run_migration")
    def test_migrate_success(self, mock_migrate, runner, mock_create_deps):
        mock_migrate.return_value = None
        result = runner.invoke(cli, ["migrate"])
        assert result.exit_code == 0
        assert "Migration complete" in result.output
