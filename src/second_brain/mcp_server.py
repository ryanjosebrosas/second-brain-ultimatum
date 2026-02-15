"""MCP Server for AI Second Brain.

Exposes recall and ask agents as tools callable from Claude Code.
Run: python -m second_brain.mcp_server
"""

import logging

from fastmcp import FastMCP

from second_brain.config import BrainConfig
from second_brain.deps import BrainDeps
from second_brain.models import get_model
from second_brain.services.memory import MemoryService
from second_brain.services.storage import StorageService
from second_brain.agents.recall import recall_agent
from second_brain.agents.ask import ask_agent
from second_brain.agents.learn import learn_agent

logger = logging.getLogger(__name__)

# Initialize server
server = FastMCP("Second Brain")

# Lazy-init deps (created on first tool call)
_deps: BrainDeps | None = None
_model = None


def _get_deps() -> BrainDeps:
    global _deps, _model
    if _deps is None:
        config = BrainConfig()
        graphiti = None
        if config.graph_provider == "graphiti":
            try:
                from second_brain.services.graphiti import GraphitiService
                graphiti = GraphitiService(config)
            except ImportError:
                logger.warning("graphiti-core not installed for MCP server")

        _deps = BrainDeps(
            config=config,
            memory_service=MemoryService(config),
            storage_service=StorageService(config),
            graphiti_service=graphiti,
        )
        _model = get_model(config)
    return _deps


def _get_model():
    _get_deps()  # ensure initialized
    return _model


@server.tool()
async def recall(query: str) -> str:
    """Search your Second Brain's memory for relevant context, patterns,
    and past experiences. Returns ranked results with sources.

    Args:
        query: What to search for (e.g., "content writing patterns",
               "enterprise objection handling", "past LinkedIn work")
    """
    deps = _get_deps()
    model = _get_model()
    result = await recall_agent.run(
        f"Search memory for: {query}",
        deps=deps,
        model=model,
    )
    output = result.output

    # Format as readable text for Claude Code
    parts = [f"# Recall: {output.query}\n"]
    if output.matches:
        parts.append("## Matches\n")
        for m in output.matches:
            parts.append(f"- [{m.relevance}] {m.content}")
            if m.source:
                parts.append(f"  Source: {m.source}")
    if output.patterns:
        parts.append("\n## Related Patterns\n")
        for p in output.patterns:
            parts.append(f"- {p}")
    if output.relations:
        parts.append("\n## Graph Relationships\n")
        for rel in output.relations:
            parts.append(f"- {rel.source} --[{rel.relationship}]--> {rel.target}")
    if output.summary:
        parts.append(f"\n## Summary\n{output.summary}")
    return "\n".join(parts)


@server.tool()
async def ask(question: str) -> str:
    """Ask your Second Brain a question. Gets instant help powered by
    accumulated knowledge: company context, customer insights, content
    patterns, style preferences, and past experiences.

    Args:
        question: Your question (e.g., "Help me write a follow-up email",
                  "What's our positioning for enterprise clients?")
    """
    deps = _get_deps()
    model = _get_model()
    result = await ask_agent.run(
        question,
        deps=deps,
        model=model,
    )
    output = result.output

    # Format as readable text for Claude Code
    parts = [output.answer]
    if output.context_used:
        parts.append(f"\n---\nContext used: {', '.join(output.context_used)}")
    if output.patterns_applied:
        parts.append(f"Patterns applied: {', '.join(output.patterns_applied)}")
    if output.relations:
        parts.append("\n## Graph Relationships\n")
        for rel in output.relations:
            parts.append(f"- {rel.source} --[{rel.relationship}]--> {rel.target}")
    if output.next_action:
        parts.append(f"\nSuggested next: {output.next_action}")
    return "\n".join(parts)


@server.tool()
async def learn(content: str, category: str = "general") -> str:
    """Extract patterns and learnings from a work session or experience.
    Feed raw text and the agent will identify patterns, insights, and
    store them in your Second Brain.

    Args:
        content: Raw text from a work session, conversation, or experience
                 to extract learnings from.
        category: Experience category - content, prospects, clients, or general.
    """
    deps = _get_deps()
    model = _get_model()
    result = await learn_agent.run(
        f"Extract learnings from this work session (category: {category}):\n\n{content}",
        deps=deps,
        model=model,
    )
    output = result.output

    parts = [f"# Learn: {output.input_summary}\n"]

    if output.patterns_extracted:
        parts.append("## Patterns Extracted\n")
        for p in output.patterns_extracted:
            marker = "(reinforced)" if p.is_reinforcement else "(new)"
            parts.append(f"- [{p.confidence}] {p.name} {marker}")
            parts.append(f"  {p.pattern_text[:120]}")

    if output.insights:
        parts.append("\n## Insights\n")
        for insight in output.insights:
            parts.append(f"- {insight}")

    parts.append(f"\n## Summary")
    parts.append(f"New: {output.patterns_new} | Reinforced: {output.patterns_reinforced}")
    parts.append(output.storage_summary)

    return "\n".join(parts)


@server.tool()
async def search_examples(content_type: str | None = None) -> str:
    """Search your Second Brain's content examples — real samples of
    emails, LinkedIn posts, case studies, presentations, and more.

    Args:
        content_type: Filter by type (linkedin, email, case-study, etc.)
                      or None for all examples.
    """
    deps = _get_deps()
    examples = await deps.storage_service.get_examples(content_type=content_type)
    if not examples:
        return "No content examples found. Add examples to memory/examples/ and run migrate."
    parts = ["# Content Examples\n"]
    for e in examples:
        parts.append(f"## [{e['content_type']}] {e['title']}")
        parts.append(e.get("content", "")[:500])
        parts.append("")
    return "\n".join(parts)


@server.tool()
async def search_knowledge(category: str | None = None) -> str:
    """Search your Second Brain's knowledge repository — frameworks,
    methodologies, playbooks, research, and tools.

    Args:
        category: Filter by category (framework, methodology, playbook,
                  research, tool) or None for all.
    """
    deps = _get_deps()
    knowledge = await deps.storage_service.get_knowledge(category=category)
    if not knowledge:
        return "No knowledge entries found. Add content to memory/knowledge-repo/ and run migrate."
    parts = ["# Knowledge Repository\n"]
    for k in knowledge:
        parts.append(f"## [{k['category']}] {k['title']}")
        parts.append(k.get("content", "")[:500])
        parts.append("")
    return "\n".join(parts)


@server.tool()
async def brain_health() -> str:
    """Check the health and growth metrics of your Second Brain."""
    deps = _get_deps()
    patterns = await deps.storage_service.get_patterns()
    experiences = await deps.storage_service.get_experiences()

    total_patterns = len(patterns)
    high = len([p for p in patterns if p.get("confidence") == "HIGH"])
    medium = len([p for p in patterns if p.get("confidence") == "MEDIUM"])
    low = len([p for p in patterns if p.get("confidence") == "LOW"])

    # Topic breakdown
    topics: dict[str, int] = {}
    for p in patterns:
        t = p.get("topic", "uncategorized")
        topics[t] = topics.get(t, 0) + 1
    topic_lines = [f"  - {t}: {c}" for t, c in sorted(topics.items())]

    # Memory count
    try:
        memory_count = await deps.memory_service.get_memory_count()
    except Exception:
        memory_count = "unavailable"

    # Latest update
    latest = patterns[0].get("date_updated", "unknown") if patterns else "no patterns yet"

    # Graph status
    graph = deps.config.graph_provider or "disabled"

    parts = [
        "# Brain Health\n",
        f"Memories: {memory_count}",
        f"Patterns: {total_patterns} (HIGH: {high}, MEDIUM: {medium}, LOW: {low})",
        f"Experiences: {len(experiences)}",
        f"Graph: {graph}",
        f"Last updated: {latest}",
    ]
    if topic_lines:
        parts.append("\n## Patterns by Topic")
        parts.extend(topic_lines)

    status = "GROWING" if total_patterns > 5 else "BUILDING"
    parts.append(f"\nStatus: {status}")
    return "\n".join(parts)


if __name__ == "__main__":
    server.run()
