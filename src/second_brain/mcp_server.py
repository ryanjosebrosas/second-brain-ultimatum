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
from second_brain.agents.create import create_agent
from second_brain.schemas import CONTENT_TYPES

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
async def create_content(
    prompt: str, content_type: str = "linkedin", mode: str | None = None
) -> str:
    """Draft content in your voice using brain knowledge.
    The agent loads your voice guide, relevant examples, applicable patterns,
    and audience context, then produces a draft for human editing.

    Args:
        prompt: What to write about — e.g., "Announce our new AI automation product"
        content_type: Content type — linkedin, email, landing-page, or comment.
        mode: Communication mode — casual, professional, or formal.
              Defaults to the content type's default mode.
    """
    if content_type not in CONTENT_TYPES:
        available = ", ".join(CONTENT_TYPES.keys())
        return f"Unknown content type '{content_type}'. Available: {available}"

    type_config = CONTENT_TYPES[content_type]
    effective_mode = mode or type_config.default_mode

    deps = _get_deps()
    model = _get_model()

    enhanced = (
        f"Content type: {type_config.name} ({content_type})\n"
        f"Communication mode: {effective_mode}\n"
        f"Structure: {type_config.structure_hint}\n"
    )
    if type_config.max_words:
        enhanced += f"Target length: ~{type_config.max_words} words\n"
    enhanced += f"\nRequest: {prompt}"

    result = await create_agent.run(enhanced, deps=deps, model=model)
    output = result.output

    parts = [
        f"# Draft: {output.content_type} ({output.mode})\n",
        output.draft,
        f"\n---",
        f"**Words**: {output.word_count}",
    ]
    if output.voice_elements:
        parts.append(f"**Voice**: {', '.join(output.voice_elements)}")
    if output.patterns_applied:
        parts.append(f"**Patterns**: {', '.join(output.patterns_applied)}")
    if output.examples_referenced:
        parts.append(f"**Examples**: {', '.join(output.examples_referenced)}")
    if output.notes:
        parts.append(f"\n**Editor notes**: {output.notes}")

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
async def delete_item(table: str, item_id: str) -> str:
    """Delete an item from your Second Brain by table and ID.

    Args:
        table: Which table to delete from (pattern, experience, example, knowledge)
        item_id: The UUID of the item to delete
    """
    deps = _get_deps()
    methods = {
        "pattern": deps.storage_service.delete_pattern,
        "experience": deps.storage_service.delete_experience,
        "example": deps.storage_service.delete_example,
        "knowledge": deps.storage_service.delete_knowledge,
    }
    if table not in methods:
        return f"Invalid table '{table}'. Use: pattern, experience, example, knowledge"
    deleted = await methods[table](item_id)
    if deleted:
        return f"Deleted {table} with ID {item_id}"
    return f"No {table} found with ID {item_id}"


@server.tool()
async def brain_health() -> str:
    """Check the health and growth metrics of your Second Brain."""
    from second_brain.services.health import HealthService

    deps = _get_deps()
    metrics = await HealthService().compute(deps)

    parts = [
        "# Brain Health\n",
        f"Memories: {metrics.memory_count}",
        f"Patterns: {metrics.total_patterns} (HIGH: {metrics.high_confidence}, MEDIUM: {metrics.medium_confidence}, LOW: {metrics.low_confidence})",
        f"Experiences: {metrics.experience_count}",
        f"Graph: {metrics.graph_provider}",
        f"Last updated: {metrics.latest_update}",
    ]
    if metrics.topics:
        parts.append("\n## Patterns by Topic")
        for t, c in sorted(metrics.topics.items()):
            parts.append(f"  - {t}: {c}")
    parts.append(f"\nStatus: {metrics.status}")
    return "\n".join(parts)


if __name__ == "__main__":
    server.run()
