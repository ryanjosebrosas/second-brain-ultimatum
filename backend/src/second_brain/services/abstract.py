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


class MemoryServiceBase(ABC):
    """Abstract interface for semantic memory backends (Mem0, Graphiti, etc.)."""

    @abstractmethod
    async def add(self, content: str, metadata: dict | None = None,
                  enable_graph: bool | None = None) -> dict:
        """Add a memory. Returns result dict (may be empty on failure)."""

    @abstractmethod
    async def add_with_metadata(self, content: str, metadata: dict,
                                enable_graph: bool | None = None) -> dict:
        """Add a memory with required structured metadata. Returns result dict."""

    @abstractmethod
    async def add_multimodal(
        self,
        content_blocks: list[dict],
        metadata: dict | None = None,
        enable_graph: bool | None = None,
    ) -> dict:
        """Add a multimodal memory (images, PDFs, documents).

        Args:
            content_blocks: List of Mem0 multimodal content block dicts.
                Each block has a 'type' key and type-specific nested dict.
                Example: [{"type": "image_url", "image_url": {"url": "..."}}]
            metadata: Optional metadata dict for categorization.
            enable_graph: Override graph setting. None = use config default.

        Returns:
            Result dict from Mem0 (may be empty on failure).
        """

    @abstractmethod
    async def search(self, query: str, limit: int | None = None,
                     enable_graph: bool | None = None) -> "SearchResult":
        """Semantic search. Returns SearchResult(memories, relations, search_filters)."""

    @abstractmethod
    async def search_with_filters(
        self,
        query: str,
        metadata_filters: dict | None = None,
        limit: int = 10,
        enable_graph: bool | None = None,
    ) -> "SearchResult":
        """Search with metadata filters. Returns SearchResult."""

    @abstractmethod
    async def search_by_category(
        self, category: str, query: str, limit: int = 10
    ) -> "SearchResult":
        """Search within a category. Returns SearchResult."""

    @abstractmethod
    async def get_all(self) -> list[dict]:
        """Return all stored memories. Returns empty list if unsupported."""

    @abstractmethod
    async def get_memory_count(self) -> int:
        """Return count of stored memories. Returns 0 if unsupported."""

    @abstractmethod
    async def update_memory(
        self, memory_id: str, content: str | None = None, metadata: dict | None = None
    ) -> None:
        """Update an existing memory. No-op if unsupported."""

    @abstractmethod
    async def delete(self, memory_id: str) -> None:
        """Delete a memory by ID. No-op if unsupported."""

    @abstractmethod
    async def get_by_id(self, memory_id: str) -> dict | None:
        """Fetch a memory by ID. Returns None if unsupported."""

    @abstractmethod
    async def delete_all(self) -> int:
        """Delete all memories. Returns count deleted (0 if unsupported)."""

    @abstractmethod
    async def enable_project_graph(self) -> None:
        """Enable project graph (Mem0-specific). No-op for other backends."""

    @abstractmethod
    async def close(self) -> None:
        """Close any open connections."""


class StubMemoryService(MemoryServiceBase):
    """No-op memory service for memory_provider='none' or testing."""

    async def add(self, content, metadata=None, enable_graph=None):
        return {}

    async def add_with_metadata(self, content, metadata, enable_graph=None):
        return {}

    async def add_multimodal(self, content_blocks, metadata=None, enable_graph=None):
        return {}

    async def search(self, query, limit=None, enable_graph=None):
        from second_brain.services.search_result import SearchResult
        return SearchResult()

    async def search_with_filters(self, query, metadata_filters=None, limit=10,
                                  enable_graph=None):
        from second_brain.services.search_result import SearchResult
        return SearchResult()

    async def search_by_category(self, category, query, limit=10):
        from second_brain.services.search_result import SearchResult
        return SearchResult()

    async def get_all(self):
        return []

    async def get_memory_count(self):
        return 0

    async def update_memory(self, memory_id, content=None, metadata=None):
        return None

    async def delete(self, memory_id):
        return None

    async def get_by_id(self, memory_id):
        return None

    async def delete_all(self):
        return 0

    async def enable_project_graph(self):
        return None

    async def close(self):
        return None
