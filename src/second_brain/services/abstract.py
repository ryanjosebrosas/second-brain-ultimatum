"""Abstract service interfaces for external integrations.

These interfaces define contracts for services that require external APIs
(Gmail, Google Calendar, PostgreSQL analytics, etc.). Concrete implementations
will be added when the APIs are available. Agents use these interfaces via
BrainDeps injection.
"""

from abc import ABC, abstractmethod


class EmailServiceBase(ABC):
    """Interface for email operations (Gmail, Outlook, etc.)."""

    @abstractmethod
    async def send(self, to: list[str], subject: str, body: str, cc: list[str] | None = None) -> dict:
        """Send an email. Returns delivery status dict."""

    @abstractmethod
    async def draft(self, to: list[str], subject: str, body: str) -> dict:
        """Create a draft email. Returns draft metadata."""

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search emails by query. Returns list of email summaries."""

    @abstractmethod
    async def get_thread(self, thread_id: str) -> list[dict]:
        """Get full email thread. Returns list of messages."""


class CalendarServiceBase(ABC):
    """Interface for calendar operations (Google Calendar, etc.)."""

    @abstractmethod
    async def get_events(self, date: str, days: int = 1) -> list[dict]:
        """Get events for date range. Returns list of event dicts."""

    @abstractmethod
    async def create_event(self, summary: str, start: str, end: str, description: str = "") -> dict:
        """Create calendar event. Returns event metadata."""

    @abstractmethod
    async def get_available_slots(self, date: str, duration_minutes: int = 60) -> list[dict]:
        """Find available time slots. Returns list of slot dicts."""


class AnalyticsServiceBase(ABC):
    """Interface for data analytics (PostgreSQL, Stripe, GA, etc.)."""

    @abstractmethod
    async def query(self, sql: str) -> list[dict]:
        """Execute analytics query. Returns list of result rows."""

    @abstractmethod
    async def get_metrics(self, metric_names: list[str], period_days: int = 30) -> dict:
        """Get named metrics for period. Returns metric name → value dict."""

    @abstractmethod
    async def get_revenue(self, period_days: int = 30) -> dict:
        """Get revenue metrics. Returns revenue summary dict."""


class TaskManagementServiceBase(ABC):
    """Interface for task/project management (Todoist, Linear, etc.)."""

    @abstractmethod
    async def get_tasks(self, status: str | None = None, limit: int = 20) -> list[dict]:
        """Get tasks optionally filtered by status. Returns task list."""

    @abstractmethod
    async def create_task(self, title: str, description: str = "", priority: int = 0) -> dict:
        """Create a task. Returns task metadata."""

    @abstractmethod
    async def update_task(self, task_id: str, status: str | None = None, **kwargs) -> dict:
        """Update task fields. Returns updated task."""


# --- Stub implementations for testing and development ---


class StubEmailService(EmailServiceBase):
    """Stub email service that logs operations without sending."""

    async def send(self, to, subject, body, cc=None):
        return {"status": "stub", "to": to, "subject": subject}

    async def draft(self, to, subject, body):
        return {"status": "stub_draft", "to": to, "subject": subject}

    async def search(self, query, limit=10):
        return []

    async def get_thread(self, thread_id):
        return []


class StubCalendarService(CalendarServiceBase):
    """Stub calendar service that returns empty results."""

    async def get_events(self, date, days=1):
        return []

    async def create_event(self, summary, start, end, description=""):
        return {"status": "stub", "summary": summary, "start": start, "end": end}

    async def get_available_slots(self, date, duration_minutes=60):
        return []


class StubAnalyticsService(AnalyticsServiceBase):
    """Stub analytics service that returns empty results."""

    async def query(self, sql):
        return []

    async def get_metrics(self, metric_names, period_days=30):
        return {name: 0 for name in metric_names}

    async def get_revenue(self, period_days=30):
        return {"total": 0, "period_days": period_days}


class StubTaskManagementService(TaskManagementServiceBase):
    """Stub task management service."""

    async def get_tasks(self, status=None, limit=20):
        return []

    async def create_task(self, title, description="", priority=0):
        return {"status": "stub", "title": title}

    async def update_task(self, task_id, status=None, **kwargs):
        return {"status": "stub", "task_id": task_id}
