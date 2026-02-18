"""Tests for Pydantic output schemas and content type utilities."""

import pytest
from pydantic import ValidationError

from second_brain.schemas import (
    RecallResult,
    AskResult,
    LearnResult,
    CreateResult,
    ReviewResult,
    MemoryMatch,
    Relation,
    PatternExtract,
    DimensionScore,
    ContentTypeConfig,
    ReviewDimensionConfig,
    GrowthEvent,
    ReviewHistoryEntry,
    ConfidenceTransition,
    GrowthSummary,
    ProjectResult,
    ProjectArtifact,
    QualityTrend,
    BrainGrowthStatus,
    BrainMilestone,
    PatternRegistryEntry,
    SetupStatus,
    DimensionBreakdown,
    BRAIN_MILESTONES,
    BRAIN_LEVEL_THRESHOLDS,
    QUALITY_GATE_SCORE,
    DEFAULT_CONTENT_TYPES,
    DEFAULT_REVIEW_DIMENSIONS,
    REVIEW_DIMENSIONS,
    content_type_from_row,
)


class TestMemoryMatch:
    """Tests for MemoryMatch schema."""

    def test_required_content(self):
        match = MemoryMatch(content="test memory")
        assert match.content == "test memory"

    def test_defaults(self):
        match = MemoryMatch(content="test")
        assert match.source == ""
        assert match.relevance == "MEDIUM"

    def test_custom_fields(self):
        match = MemoryMatch(content="x", source="file.md", relevance="HIGH")
        assert match.source == "file.md"
        assert match.relevance == "HIGH"


class TestRelation:
    """Tests for Relation schema."""

    def test_all_required(self):
        rel = Relation(source="A", relationship="uses", target="B")
        assert rel.source == "A"
        assert rel.relationship == "uses"
        assert rel.target == "B"

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            Relation(source="A", relationship="uses")


class TestRecallResult:
    """Tests for RecallResult output schema."""

    def test_defaults(self):
        result = RecallResult(query="test")
        assert result.query == "test"
        assert result.matches == []
        assert result.patterns == []
        assert result.relations == []
        assert result.summary == ""

    def test_with_matches(self):
        match = MemoryMatch(content="test memory", source="mem0", relevance="HIGH")
        result = RecallResult(query="test", matches=[match], summary="Found 1")
        assert len(result.matches) == 1
        assert result.matches[0].relevance == "HIGH"

    def test_list_default_not_shared(self):
        """Two instances don't share the same default list."""
        r1 = RecallResult(query="a")
        r2 = RecallResult(query="b")
        r1.matches.append(MemoryMatch(content="x"))
        assert len(r2.matches) == 0


class TestAskResult:
    """Tests for AskResult output schema."""

    def test_defaults(self):
        result = AskResult(answer="test answer")
        assert result.answer == "test answer"
        assert result.context_used == []
        assert result.patterns_applied == []
        assert result.confidence == "MEDIUM"
        assert result.next_action == ""

    def test_confidence_values(self):
        for level in ["LOW", "MEDIUM", "HIGH"]:
            result = AskResult(answer="ok", confidence=level)
            assert result.confidence == level

    def test_invalid_confidence_raises(self):
        with pytest.raises(ValidationError):
            AskResult(answer="ok", confidence="INVALID")

    def test_answer_field_description_is_explicit(self):
        """Guard against vague answer field descriptions that cause summary output."""
        field_info = AskResult.model_fields["answer"]
        desc = field_info.description.lower()
        assert "complete" in desc or "full" in desc, (
            "answer field description must explicitly require complete/full response"
        )
        assert "not" in desc or "never" in desc, (
            "answer field description must include anti-pattern guidance"
        )


class TestPatternExtract:
    """Tests for PatternExtract schema."""

    def test_required_fields(self):
        p = PatternExtract(
            name="Hook First", topic="Content", pattern_text="Start with a hook"
        )
        assert p.name == "Hook First"
        assert p.confidence == "LOW"
        assert p.is_reinforcement is False

    def test_optional_fields(self):
        p = PatternExtract(
            name="Test",
            topic="T",
            pattern_text="text",
            evidence=["ev1"],
            anti_patterns=["ap1"],
            context="when posting",
            is_reinforcement=True,
            existing_pattern_name="Old Pattern",
            applicable_content_types=["linkedin"],
        )
        assert p.evidence == ["ev1"]
        assert p.applicable_content_types == ["linkedin"]

    def test_applicable_content_types_none_means_universal(self):
        p = PatternExtract(name="T", topic="T", pattern_text="t")
        assert p.applicable_content_types is None


class TestLearnResult:
    """Tests for LearnResult output schema."""

    def test_defaults(self):
        result = LearnResult(input_summary="session summary")
        assert result.patterns_extracted == []
        assert result.insights == []
        assert result.experience_recorded is False
        assert result.patterns_new == 0
        assert result.patterns_reinforced == 0


class TestCreateResult:
    """Tests for CreateResult output schema."""

    def test_required_fields(self):
        result = CreateResult(
            draft="Hello world",
            content_type="linkedin",
            mode="casual",
        )
        assert result.draft == "Hello world"
        assert result.word_count == 0

    def test_optional_lists_default_empty(self):
        result = CreateResult(draft="x", content_type="t", mode="m")
        assert result.voice_elements == []
        assert result.patterns_applied == []
        assert result.examples_referenced == []

    def test_draft_field_description_is_explicit(self):
        """Guard against vague draft field descriptions that cause summary output."""
        field_info = CreateResult.model_fields["draft"]
        desc = field_info.description.lower()
        assert "complete" in desc or "full" in desc, (
            "draft field description must explicitly require complete/full text"
        )
        assert "not" in desc or "never" in desc, (
            "draft field description must include anti-pattern guidance"
        )

    def test_notes_field_description_separates_from_draft(self):
        """Verify notes field description clarifies it's for meta-commentary."""
        field_info = CreateResult.model_fields["notes"]
        desc = field_info.description.lower()
        assert "note" in desc or "editorial" in desc or "suggestion" in desc


class TestDimensionScore:
    """Tests for DimensionScore schema."""

    def test_all_fields(self):
        score = DimensionScore(
            dimension="Messaging",
            score=8,
            status="pass",
            strengths=["Clear"],
            suggestions=["Be bolder"],
            issues=[],
        )
        assert score.dimension == "Messaging"
        assert score.score == 8


class TestReviewResult:
    """Tests for ReviewResult output schema."""

    def test_required_fields(self):
        result = ReviewResult(
            scores=[],
            overall_score=7.5,
            verdict="NEEDS REVISION",
        )
        assert result.overall_score == 7.5
        assert result.verdict == "NEEDS REVISION"
        assert result.summary == ""

    def test_default_lists(self):
        result = ReviewResult(scores=[], overall_score=5.0, verdict="MAJOR REWORK")
        assert result.top_strengths == []
        assert result.critical_issues == []
        assert result.next_steps == []


class TestContentTypeConfig:
    """Tests for ContentTypeConfig and related utilities."""

    def test_default_content_types_exist(self):
        assert "linkedin" in DEFAULT_CONTENT_TYPES
        assert "email" in DEFAULT_CONTENT_TYPES
        assert "landing-page" in DEFAULT_CONTENT_TYPES
        assert "comment" in DEFAULT_CONTENT_TYPES

    def test_all_builtin_types(self):
        expected = {
            "linkedin", "email", "landing-page", "comment",
            "case-study", "proposal", "one-pager", "presentation", "instagram",
            "essay",
        }
        assert set(DEFAULT_CONTENT_TYPES.keys()) == expected

    def test_builtin_types_are_builtin(self):
        for slug, config in DEFAULT_CONTENT_TYPES.items():
            assert config.is_builtin is True, f"{slug} should be is_builtin=True"

    def test_content_type_from_row_full(self):
        row = {
            "slug": "test-type",
            "name": "Test Type",
            "description": "A test content type",
            "max_words": 500,
            "structure_hint": "Hook | Body | CTA",
            "default_mode": "professional",
            "example_type": "test-type",
            "review_dimensions": [
                {"name": "Messaging", "weight": 1.5, "enabled": True}
            ],
            "is_builtin": False,
        }
        config = content_type_from_row(row)
        assert config.name == "Test Type"
        assert config.max_words == 500
        assert config.is_builtin is False
        assert len(config.review_dimensions) == 1
        assert config.review_dimensions[0].weight == 1.5

    def test_content_type_from_row_minimal(self):
        row = {"name": "Minimal", "slug": "minimal"}
        config = content_type_from_row(row)
        assert config.name == "Minimal"
        assert config.default_mode == "professional"
        assert config.max_words == 0
        assert config.review_dimensions is None

    def test_content_type_from_row_no_review_dimensions(self):
        row = {"name": "T", "review_dimensions": None}
        config = content_type_from_row(row)
        assert config.review_dimensions is None

    def test_content_type_from_row_empty_review_dimensions(self):
        row = {"name": "T", "review_dimensions": []}
        config = content_type_from_row(row)
        assert config.review_dimensions is None  # empty list treated as falsy


class TestReviewDimensions:
    """Tests for REVIEW_DIMENSIONS constant and defaults."""

    def test_review_dimensions_not_empty(self):
        assert len(REVIEW_DIMENSIONS) > 0

    def test_review_dimensions_have_required_keys(self):
        for dim in REVIEW_DIMENSIONS:
            assert "name" in dim
            assert "focus" in dim
            assert "checks" in dim

    def test_default_review_dimensions_match_count(self):
        assert len(DEFAULT_REVIEW_DIMENSIONS) == len(REVIEW_DIMENSIONS)

    def test_default_review_dimensions_all_enabled(self):
        for dim_cfg in DEFAULT_REVIEW_DIMENSIONS:
            assert dim_cfg.enabled is True
            assert dim_cfg.weight == 1.0


class TestGrowthEvent:
    """Tests for GrowthEvent schema."""

    def test_defaults(self):
        event = GrowthEvent(event_type="pattern_created")
        assert event.event_date == ""
        assert event.pattern_name == ""
        assert event.details == {}


class TestGrowthSummary:
    """Tests for GrowthSummary schema."""

    def test_defaults(self):
        summary = GrowthSummary(period_days=30)
        assert summary.patterns_created == 0
        assert summary.review_score_trend == "stable"
        assert summary.stale_patterns == []
        assert summary.top_patterns == []


class TestConfidenceTransition:
    """Tests for ConfidenceTransition schema."""

    def test_required_fields(self):
        ct = ConfidenceTransition(
            pattern_name="Hook First",
            from_confidence="LOW",
            to_confidence="MEDIUM",
        )
        assert ct.pattern_name == "Hook First"
        assert ct.use_count == 1


class TestReviewHistoryEntry:
    """Tests for ReviewHistoryEntry schema."""

    def test_required_fields(self):
        entry = ReviewHistoryEntry(overall_score=8.0, verdict="READY TO SEND")
        assert entry.overall_score == 8.0
        assert entry.content_preview == ""
        assert entry.dimension_scores == []


class TestProjectSchemas:
    """Tests for project lifecycle schemas and constants."""

    def test_project_result_defaults(self):
        pr = ProjectResult(
            project_id="proj-1", name="Test", lifecycle_stage="planning"
        )
        assert pr.project_id == "proj-1"
        assert pr.category == "content"
        assert pr.artifacts == []
        assert pr.review_score is None
        assert pr.patterns_extracted == []
        assert pr.patterns_upgraded == []
        assert pr.message == ""

    def test_project_result_with_artifacts(self):
        art = ProjectArtifact(artifact_type="plan", title="My Plan")
        pr = ProjectResult(
            project_id="p1", name="Test", lifecycle_stage="executing",
            artifacts=[art],
        )
        assert len(pr.artifacts) == 1
        assert pr.artifacts[0].artifact_type == "plan"

    def test_project_artifact_defaults(self):
        art = ProjectArtifact(artifact_type="output")
        assert art.title is None
        assert art.content is None
        assert art.metadata == {}

    def test_quality_trend_defaults(self):
        qt = QualityTrend(period_days=30)
        assert qt.total_reviews == 0
        assert qt.avg_score == 0.0
        assert qt.score_trend == "stable"
        assert qt.by_dimension == []
        assert qt.by_content_type == {}
        assert qt.recurring_issues == []
        assert qt.excellence_count == 0
        assert qt.needs_work_count == 0

    def test_dimension_breakdown(self):
        db = DimensionBreakdown(dimension="Messaging", avg_score=8.5)
        assert db.dimension == "Messaging"
        assert db.trend == "stable"
        assert db.review_count == 0

    def test_brain_growth_status_defaults(self):
        bg = BrainGrowthStatus(level="EMPTY", level_description="No data yet")
        assert bg.milestones == []
        assert bg.next_milestone is None
        assert bg.patterns_total == 0
        assert bg.high_confidence_count == 0
        assert bg.experiences_total == 0
        assert bg.avg_review_score == 0.0

    def test_brain_milestone(self):
        bm = BrainMilestone(name="first_pattern", description="Extract first pattern")
        assert bm.completed is False
        assert bm.completed_date is None

    def test_brain_milestone_completed(self):
        bm = BrainMilestone(
            name="first_pattern", description="Extract first pattern",
            completed=True, completed_date="2026-01-15",
        )
        assert bm.completed is True
        assert bm.completed_date == "2026-01-15"

    def test_pattern_registry_entry(self):
        pre = PatternRegistryEntry(
            name="Hook First", topic="LinkedIn", confidence="HIGH",
            date_added="2026-01-01", date_updated="2026-02-01",
        )
        assert pre.use_count == 0
        assert pre.consecutive_failures == 0
        assert pre.is_stale is False
        assert pre.applicable_content_types == []

    def test_setup_status_defaults(self):
        ss = SetupStatus()
        assert ss.is_complete is False
        assert ss.steps == []
        assert ss.missing_categories == []
        assert ss.total_memory_entries == 0
        assert ss.has_patterns is False
        assert ss.has_examples is False

    def test_growth_summary_new_fields(self):
        gs = GrowthSummary(period_days=30)
        assert gs.brain_level == "EMPTY"
        assert gs.milestones_completed == 0
        assert gs.quality_trend is None

    def test_brain_milestones_constant(self):
        assert isinstance(BRAIN_MILESTONES, list)
        assert len(BRAIN_MILESTONES) == 9
        names = [m["name"] for m in BRAIN_MILESTONES]
        assert "first_pattern" in names
        assert "compound_returns" in names

    def test_brain_level_thresholds_constant(self):
        assert isinstance(BRAIN_LEVEL_THRESHOLDS, dict)
        assert set(BRAIN_LEVEL_THRESHOLDS.keys()) == {
            "EMPTY", "FOUNDATION", "GROWTH", "COMPOUND", "EXPERT"
        }

    def test_quality_gate_score_constant(self):
        assert QUALITY_GATE_SCORE == 8.0
