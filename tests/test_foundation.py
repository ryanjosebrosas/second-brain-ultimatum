"""Tests for agentic brain upgrade foundation: schemas, services, config."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from second_brain.schemas import (
    RoutingDecision, EssayResult, ClarityFinding, ClarityResult,
    SynthesizerTheme, SynthesizerResult, TemplateOpportunity,
    TemplateBuilderResult, CoachSession, PriorityScore, PMOResult,
    EmailAction,
    SpecialistAnswer,
)
from second_brain.services.abstract import (
    EmailServiceBase, CalendarServiceBase, AnalyticsServiceBase,
    TaskManagementServiceBase, StubEmailService, StubCalendarService,
    StubAnalyticsService, StubTaskManagementService,
)
from second_brain.config import BrainConfig
from second_brain.deps import BrainDeps


# --- Schema Tests ---

class TestRoutingDecision:
    def test_defaults(self):
        r = RoutingDecision(target_agent="recall", reasoning="memory search needed")
        assert r.target_agent == "recall"
        assert r.pipeline_steps == []
        assert r.confidence == "MEDIUM"

    def test_pipeline_mode(self):
        r = RoutingDecision(
            target_agent="pipeline",
            reasoning="multi-step workflow",
            pipeline_steps=["recall", "ask", "create"],
        )
        assert len(r.pipeline_steps) == 3

    def test_context_to_inject(self):
        r = RoutingDecision(
            target_agent="ask",
            reasoning="needs context",
            context_to_inject=["voice_guide", "patterns"],
        )
        assert len(r.context_to_inject) == 2

    def test_invalid_agent_rejected(self):
        with pytest.raises(Exception):
            RoutingDecision(target_agent="nonexistent", reasoning="test")

    def test_high_confidence(self):
        r = RoutingDecision(target_agent="recall", reasoning="clear memory search", confidence="HIGH")
        assert r.confidence == "HIGH"


class TestEssayResult:
    def test_defaults(self):
        e = EssayResult(title="Test", essay="Full essay text here")
        assert e.stirc_score == 0
        assert e.word_count == 0
        assert e.patterns_applied == []
        assert e.notes == ""

    def test_full(self):
        e = EssayResult(
            title="Why AI Agents Matter",
            essay="Long essay content...",
            stirc_score=22,
            framework="argumentative",
            word_count=1500,
            patterns_applied=["hook_pattern"],
        )
        assert e.stirc_score == 22
        assert e.framework == "argumentative"
        assert len(e.patterns_applied) == 1


class TestClarityFinding:
    def test_required_fields(self):
        f = ClarityFinding(
            severity="HIGH",
            location="paragraph 3",
            issue="Undefined acronym",
            suggestion="Define on first use",
        )
        assert f.severity == "HIGH"
        assert f.pattern == ""

    def test_invalid_severity(self):
        with pytest.raises(Exception):
            ClarityFinding(
                severity="EXTREME",
                location="intro",
                issue="issue",
                suggestion="fix it",
            )


class TestClarityResult:
    def test_empty(self):
        c = ClarityResult()
        assert c.findings == []
        assert c.critical_count == 0
        assert c.overall_readability == "MEDIUM"

    def test_with_findings(self):
        finding = ClarityFinding(
            severity="HIGH",
            location="paragraph 3",
            issue="Undefined acronym: ROI",
            suggestion="Define ROI on first use",
            pattern="jargon",
        )
        c = ClarityResult(findings=[finding], critical_count=0)
        assert len(c.findings) == 1
        assert c.findings[0].pattern == "jargon"


class TestSynthesizerTheme:
    def test_required_fields(self):
        t = SynthesizerTheme(
            title="Strengthen Hook",
            priority="HIGH",
            action="Rewrite first sentence",
        )
        assert t.effort_minutes == 30
        assert t.owner == "user"
        assert t.findings_consolidated == []

    def test_with_dependencies(self):
        t = SynthesizerTheme(
            title="Add Data",
            priority="MEDIUM",
            action="Insert statistics",
            dependencies=["Strengthen Hook"],
        )
        assert len(t.dependencies) == 1


class TestSynthesizerResult:
    def test_empty(self):
        s = SynthesizerResult()
        assert s.themes == []
        assert s.implementation_hours == 0.0
        assert s.parallel_opportunities == []

    def test_with_themes(self):
        theme = SynthesizerTheme(title="Fix Hook", priority="HIGH", action="Rewrite")
        s = SynthesizerResult(
            themes=[theme],
            total_findings_input=5,
            total_themes_output=1,
        )
        assert len(s.themes) == 1
        assert s.total_findings_input == 5


class TestTemplateOpportunity:
    def test_required_fields(self):
        t = TemplateOpportunity(
            name="Cold Outreach Template",
            source_deliverable="Q4 email campaign",
            structure="Hook -> Value -> CTA",
            when_to_use="Cold prospect outreach",
        )
        assert t.customization_guide == ""
        assert t.estimated_time_savings == ""


class TestTemplateBuilderResult:
    def test_empty(self):
        r = TemplateBuilderResult()
        assert r.opportunities == []
        assert r.templates_created == 0


class TestCoachSession:
    def test_defaults(self):
        s = CoachSession(session_type="morning")
        assert s.priorities == []
        assert s.therapeutic_level == 1
        assert s.next_action == ""

    def test_evening_session(self):
        s = CoachSession(
            session_type="evening",
            coaching_notes="Good focus today",
            therapeutic_level=2,
        )
        assert s.session_type == "evening"
        assert s.therapeutic_level == 2

    def test_invalid_session_type(self):
        with pytest.raises(Exception):
            CoachSession(session_type="weekend")


class TestPriorityScore:
    def test_required_fields(self):
        p = PriorityScore(task_name="Fix auth bug", total_score=85.0)
        assert p.category == "backlog"
        assert p.rationale == ""

    def test_full_scoring(self):
        p = PriorityScore(
            task_name="Fix auth bug",
            total_score=85.0,
            urgency=9.0,
            impact=8.0,
            effort=7.0,
            alignment=8.0,
            momentum=7.0,
            category="today_focus",
        )
        assert p.category == "today_focus"


class TestPMOResult:
    def test_defaults(self):
        p = PMOResult()
        assert p.scored_tasks == []
        assert p.capacity_hours == 8.0
        assert p.today_focus == []

    def test_with_scores(self):
        score = PriorityScore(
            task_name="Fix auth bug",
            total_score=85.0,
            urgency=9.0,
            impact=8.0,
            category="today_focus",
        )
        p = PMOResult(scored_tasks=[score], today_focus=["Fix auth bug"])
        assert p.scored_tasks[0].total_score == 85.0
        assert "Fix auth bug" in p.today_focus


class TestEmailAction:
    def test_send(self):
        e = EmailAction(
            action_type="send",
            subject="Follow up",
            body="Hi...",
            recipients=["sarah@example.com"],
            status="sent",
        )
        assert e.action_type == "send"
        assert e.status == "sent"

    def test_draft_defaults(self):
        e = EmailAction(action_type="draft")
        assert e.subject == ""
        assert e.status == "draft"

    def test_invalid_action_type(self):
        with pytest.raises(Exception):
            EmailAction(action_type="forward")


class TestSpecialistAnswer:
    def test_verified(self):
        s = SpecialistAnswer(
            answer="Use @agent.tool decorator",
            confidence_level="VERIFIED",
            sources=["src/agents/recall.py"],
        )
        assert s.confidence_level == "VERIFIED"
        assert len(s.sources) == 1

    def test_uncertain(self):
        s = SpecialistAnswer(
            answer="Possibly use run() method",
            confidence_level="UNCERTAIN",
        )
        assert s.related_topics == []

    def test_invalid_confidence(self):
        with pytest.raises(Exception):
            SpecialistAnswer(answer="test", confidence_level="MAYBE")


# --- Abstract Service Tests ---

class TestStubEmailService:
    @pytest.mark.asyncio
    async def test_send(self):
        svc = StubEmailService()
        result = await svc.send(["test@example.com"], "Subject", "Body")
        assert result["status"] == "stub"
        assert result["to"] == ["test@example.com"]

    @pytest.mark.asyncio
    async def test_draft(self):
        svc = StubEmailService()
        result = await svc.draft(["test@example.com"], "Subject", "Body")
        assert result["status"] == "stub_draft"

    @pytest.mark.asyncio
    async def test_search(self):
        svc = StubEmailService()
        result = await svc.search("test query")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_thread(self):
        svc = StubEmailService()
        result = await svc.get_thread("thread-123")
        assert result == []

    def test_is_abstract_subclass(self):
        assert issubclass(StubEmailService, EmailServiceBase)


class TestStubCalendarService:
    @pytest.mark.asyncio
    async def test_get_events(self):
        svc = StubCalendarService()
        result = await svc.get_events("2026-02-17")
        assert result == []

    @pytest.mark.asyncio
    async def test_create_event(self):
        svc = StubCalendarService()
        result = await svc.create_event("Meeting", "09:00", "10:00")
        assert result["status"] == "stub"
        assert result["summary"] == "Meeting"

    @pytest.mark.asyncio
    async def test_get_available_slots(self):
        svc = StubCalendarService()
        result = await svc.get_available_slots("2026-02-17")
        assert result == []


class TestStubAnalyticsService:
    @pytest.mark.asyncio
    async def test_query(self):
        svc = StubAnalyticsService()
        result = await svc.query("SELECT 1")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_metrics(self):
        svc = StubAnalyticsService()
        result = await svc.get_metrics(["revenue", "users"])
        assert result == {"revenue": 0, "users": 0}

    @pytest.mark.asyncio
    async def test_get_revenue(self):
        svc = StubAnalyticsService()
        result = await svc.get_revenue(period_days=7)
        assert result["total"] == 0
        assert result["period_days"] == 7


class TestStubTaskService:
    @pytest.mark.asyncio
    async def test_get_tasks(self):
        svc = StubTaskManagementService()
        result = await svc.get_tasks()
        assert result == []

    @pytest.mark.asyncio
    async def test_create_task(self):
        svc = StubTaskManagementService()
        result = await svc.create_task("Write tests")
        assert result["status"] == "stub"
        assert result["title"] == "Write tests"

    @pytest.mark.asyncio
    async def test_update_task(self):
        svc = StubTaskManagementService()
        result = await svc.update_task("task-123", status="done")
        assert result["task_id"] == "task-123"


def test_abstract_interfaces_not_instantiable():
    """Abstract base classes cannot be instantiated directly."""
    with pytest.raises(TypeError):
        EmailServiceBase()
    with pytest.raises(TypeError):
        CalendarServiceBase()
    with pytest.raises(TypeError):
        AnalyticsServiceBase()
    with pytest.raises(TypeError):
        TaskManagementServiceBase()


def _make_config(tmp_path=None):
    """Create a minimal BrainConfig for testing."""
    return BrainConfig(
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
        brain_data_path=tmp_path or "/tmp",
        _env_file=None,
    )


# --- Config Tests ---

class TestAgenticConfig:
    def test_agentic_defaults(self, tmp_path):
        config = _make_config(tmp_path)
        assert config.agent_max_retries == 3
        assert config.agent_request_limit == 10
        assert config.pipeline_request_limit == 30
        assert config.stirc_threshold == 18

    def test_coach_defaults(self, tmp_path):
        config = _make_config(tmp_path)
        assert config.coach_pomodoro_minutes == 25
        assert config.coach_break_minutes == 5

    def test_pmo_weights(self, tmp_path):
        config = _make_config(tmp_path)
        weights = config.pmo_score_weights
        assert abs(sum(weights.values()) - 1.0) < 0.01
        assert "urgency" in weights
        assert "impact" in weights
        assert "effort" in weights
        assert "alignment" in weights
        assert "momentum" in weights


# --- BrainDeps Tests ---

class TestBrainDepsExtension:
    def test_new_optional_services_default_none(self, tmp_path):
        config = _make_config(tmp_path)
        deps = BrainDeps(
            config=config,
            memory_service=MagicMock(),
            storage_service=MagicMock(),
        )
        assert deps.email_service is None
        assert deps.calendar_service is None
        assert deps.analytics_service is None
        assert deps.task_service is None

    def test_inject_stub_services(self, tmp_path):
        config = _make_config(tmp_path)
        deps = BrainDeps(
            config=config,
            memory_service=MagicMock(),
            storage_service=MagicMock(),
            email_service=StubEmailService(),
            calendar_service=StubCalendarService(),
        )
        assert deps.email_service is not None
        assert deps.calendar_service is not None
        assert isinstance(deps.email_service, EmailServiceBase)

    def test_inject_all_stub_services(self, tmp_path):
        config = _make_config(tmp_path)
        deps = BrainDeps(
            config=config,
            memory_service=MagicMock(),
            storage_service=MagicMock(),
            email_service=StubEmailService(),
            calendar_service=StubCalendarService(),
            analytics_service=StubAnalyticsService(),
            task_service=StubTaskManagementService(),
        )
        assert deps.analytics_service is not None
        assert deps.task_service is not None

    def test_fields_exist_in_dataclass(self):
        fields = BrainDeps.__dataclass_fields__
        assert "email_service" in fields
        assert "calendar_service" in fields
        assert "analytics_service" in fields
        assert "task_service" in fields
