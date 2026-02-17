"""MCP Server for AI Second Brain.

Exposes recall and ask agents as tools callable from Claude Code.
Run: python -m second_brain.mcp_server
"""

import asyncio
import logging
from typing import TYPE_CHECKING

from fastmcp import FastMCP

if TYPE_CHECKING:
    from pydantic_ai.models import Model

from second_brain.deps import BrainDeps, create_deps
from second_brain.models import get_model
from second_brain.agents.recall import recall_agent
from second_brain.agents.ask import ask_agent
from second_brain.agents.learn import learn_agent
from second_brain.agents.create import create_agent
from second_brain.agents.review import run_full_review

logger = logging.getLogger(__name__)

MAX_INPUT_LENGTH = 10000  # Characters


def _validate_mcp_input(text: str, label: str = "input") -> str:
    """Validate MCP tool text input."""
    if not text or not text.strip():
        raise ValueError(f"{label} cannot be empty")
    if len(text) > MAX_INPUT_LENGTH:
        raise ValueError(
            f"{label} too long ({len(text)} chars, max {MAX_INPUT_LENGTH})"
        )
    return text.strip()


# Initialize server
server = FastMCP("Second Brain")

# Lazy-init deps (created on first tool call) with circuit breaker
_deps: BrainDeps | None = None
_model = None
_deps_failed: bool = False
_deps_error: str = ""


def _get_deps() -> BrainDeps:
    global _deps, _model, _deps_failed, _deps_error
    if _deps_failed:
        raise RuntimeError(
            f"Second Brain initialization failed: {_deps_error}. "
            "Restart the MCP server to retry."
        )
    if _deps is None:
        try:
            _deps = create_deps()
            _model = get_model(_deps.config)
        except Exception as e:
            _deps_failed = True
            _deps_error = str(e)
            logger.error("Failed to initialize deps: %s", e)
            raise RuntimeError(f"Second Brain initialization failed: {e}") from e
    return _deps


def _get_model() -> "Model | None":
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
    try:
        query = _validate_mcp_input(query, label="query")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model()
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await recall_agent.run(
                f"Search memory for: {query}",
                deps=deps,
                model=model,
            )
    except TimeoutError:
        return f"Recall timed out after {timeout}s. Try a simpler query."
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
    try:
        question = _validate_mcp_input(question, label="question")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model()
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await ask_agent.run(
                question,
                deps=deps,
                model=model,
            )
    except TimeoutError:
        return f"Ask timed out after {timeout}s. Try a simpler question."
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
    try:
        content = _validate_mcp_input(content, label="content")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model()
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await learn_agent.run(
                f"Extract learnings from this work session (category: {category}):\n\n{content}",
                deps=deps,
                model=model,
            )
    except TimeoutError:
        return f"Learn timed out after {timeout}s. Try submitting less content."
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
        content_type: Content type — linkedin, email, landing-page, comment,
                      case-study, proposal, one-pager, presentation, instagram,
                      or any custom type you've added.
        mode: Communication mode — casual, professional, or formal.
              Defaults to the content type's default mode.
    """
    try:
        prompt = _validate_mcp_input(prompt, label="prompt")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model()
    registry = deps.get_content_type_registry()

    type_config = await registry.get(content_type)
    if not type_config:
        available = await registry.slugs()
        return f"Unknown content type '{content_type}'. Available: {', '.join(available)}"

    effective_mode = mode or type_config.default_mode

    enhanced = (
        f"Content type: {type_config.name} ({content_type})\n"
        f"Communication mode: {effective_mode}\n"
        f"Structure: {type_config.structure_hint}\n"
    )
    if type_config.max_words:
        enhanced += f"Target length: ~{type_config.max_words} words\n"
    enhanced += f"\nRequest: {prompt}"

    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await create_agent.run(enhanced, deps=deps, model=model)
    except TimeoutError:
        return f"Create timed out after {timeout}s. Try a simpler prompt."
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
async def review_content(content: str, content_type: str | None = None) -> str:
    """Review content quality with adaptive dimension scoring. Returns a structured
    scorecard with per-dimension scores, overall score, and verdict.
    When content_type is provided, review dimensions are adapted to that type
    (e.g., a comment skips 'Data Accuracy', a case study weights it heavily).

    Args:
        content: The content to review (draft text, email, post, etc.)
        content_type: Optional content type for adaptive dimension scoring
                     (linkedin, email, etc.)
    """
    try:
        content = _validate_mcp_input(content, label="content")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    model = _get_model()
    timeout = deps.config.api_timeout_seconds * deps.config.mcp_review_timeout_multiplier
    try:
        async with asyncio.timeout(timeout):
            result = await run_full_review(content, deps, model, content_type)
    except TimeoutError:
        return f"Review timed out after {timeout}s. Try shorter content."

    parts = [f"# Review: {result.overall_score}/10 — {result.verdict}\n"]

    if result.summary:
        parts.append(result.summary)

    parts.append("\n| Dimension | Score | Status |")
    parts.append("|-----------|-------|--------|")
    for s in result.scores:
        parts.append(f"| {s.dimension} | {s.score}/10 | {s.status} |")

    if result.top_strengths:
        parts.append("\n## Strengths")
        for strength in result.top_strengths:
            parts.append(f"- {strength}")

    if result.critical_issues:
        parts.append("\n## Issues (Must Fix)")
        for issue in result.critical_issues:
            parts.append(f"- {issue}")

    if result.next_steps:
        parts.append("\n## Next Steps")
        for step in result.next_steps:
            parts.append(f"- {step}")

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
    try:
        item_id = _validate_mcp_input(item_id, label="item_id")
    except ValueError as e:
        return str(e)
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
    if metrics.graphiti_status != "disabled":
        parts.append(f"Graphiti: {metrics.graphiti_status} (backend: {metrics.graphiti_backend})")
    if metrics.topics:
        parts.append("\n## Patterns by Topic")
        for t, c in sorted(metrics.topics.items()):
            parts.append(f"  - {t}: {c}")
    parts.append(f"\nStatus: {metrics.status}")
    return "\n".join(parts)


@server.tool()
async def graph_search(query: str, limit: int = 10) -> str:
    """Search the Graphiti knowledge graph for entity relationships.
    Returns connections between people, concepts, patterns, and experiences
    discovered through graph traversal.

    Args:
        query: What to search for in the knowledge graph
        limit: Maximum number of relationships to return (default: 10)
    """
    deps = _get_deps()
    if not deps.graphiti_service:
        return "Graphiti is not enabled. Set GRAPHITI_ENABLED=true in your .env file."

    results = await deps.graphiti_service.search(query, limit=limit)
    if not results:
        return f"No graph relationships found for: {query}"

    parts = [f"# Graph Search: {query}\n"]
    for rel in results:
        src = rel.get("source", "?")
        relationship = rel.get("relationship", "?")
        tgt = rel.get("target", "?")
        parts.append(f"- {src} --[{relationship}]--> {tgt}")
    parts.append(f"\nFound {len(results)} relationship(s)")
    return "\n".join(parts)


@server.tool()
async def graph_health() -> str:
    """Check the health and connectivity of the Graphiti knowledge graph backend.
    Returns status, backend type, and any errors.
    """
    deps = _get_deps()
    if not deps.graphiti_service:
        return "Graphiti is not enabled. Set GRAPHITI_ENABLED=true in your .env file."

    health = await deps.graphiti_service.health_check()
    parts = [
        "# Graph Health\n",
        f"Status: {health.get('status', 'unknown')}",
        f"Backend: {health.get('backend', 'none')}",
    ]
    if health.get("error"):
        parts.append(f"Error: {health['error']}")
    return "\n".join(parts)


@server.tool()
async def consolidate_brain(min_cluster_size: int = 3) -> str:
    """Consolidate accumulated memories into patterns. Reviews recent Mem0
    memories, identifies recurring themes, and promotes them to structured
    patterns in the pattern registry.

    Args:
        min_cluster_size: Minimum memories needed to form a pattern cluster (default: 3)
    """
    deps = _get_deps()
    model = _get_model()
    timeout = deps.config.api_timeout_seconds
    try:
        async with asyncio.timeout(timeout):
            result = await learn_agent.run(
                f"Run memory consolidation with min_cluster_size={min_cluster_size}. "
                f"Use the consolidate_memories tool to review accumulated memories, "
                f"then use store_pattern and reinforce_existing_pattern to act on findings. "
                f"Tag graduated memories with tag_graduated_memories when done.",
                deps=deps,
                model=model,
            )
    except TimeoutError:
        return f"Consolidation timed out after {timeout}s. Try again later."
    output = result.output

    parts = [f"# Brain Consolidation\n", f"**Summary**: {output.input_summary}\n"]

    if output.patterns_extracted:
        parts.append("## Patterns Identified\n")
        for p in output.patterns_extracted:
            marker = "(reinforced)" if p.is_reinforcement else "(new)"
            parts.append(f"- [{p.confidence}] {p.name} {marker}")

    parts.append(
        f"\n**Results**: {output.patterns_new} new, "
        f"{output.patterns_reinforced} reinforced"
    )

    return "\n".join(parts)


@server.tool()
async def growth_report(days: int = 30) -> str:
    """Get a growth report for your Second Brain showing pattern creation,
    reinforcement, confidence upgrades, and review score trends.

    Args:
        days: Number of days to include in the report (default: 30)
    """
    from second_brain.services.health import HealthService

    deps = _get_deps()
    metrics = await HealthService().compute_growth(deps, days=days)

    parts = [
        f"# Growth Report ({days} days)\n",
        f"## Brain Status: {metrics.status}\n",
        f"Memories: {metrics.memory_count}",
        f"Patterns: {metrics.total_patterns} (HIGH: {metrics.high_confidence}, "
        f"MEDIUM: {metrics.medium_confidence}, LOW: {metrics.low_confidence})",
        f"Experiences: {metrics.experience_count}",
        f"\n## Growth Activity\n",
        f"Events total: {metrics.growth_events_total}",
        f"Patterns created: {metrics.patterns_created_period}",
        f"Patterns reinforced: {metrics.patterns_reinforced_period}",
        f"Confidence upgrades: {metrics.confidence_upgrades_period}",
    ]

    if metrics.reviews_completed_period > 0:
        parts.append(f"\n## Quality Metrics\n")
        parts.append(f"Reviews completed: {metrics.reviews_completed_period}")
        parts.append(f"Average score: {metrics.avg_review_score}/10")
        parts.append(f"Trend: {metrics.review_score_trend}")

    if metrics.stale_patterns:
        parts.append(f"\n## Stale Patterns (no activity in 30+ days)\n")
        for name in metrics.stale_patterns:
            parts.append(f"- {name}")

    if metrics.topics:
        parts.append(f"\n## Patterns by Topic")
        for t, c in sorted(metrics.topics.items()):
            parts.append(f"  - {t}: {c}")

    return "\n".join(parts)


@server.tool()
async def list_content_types() -> str:
    """List all available content types in the Second Brain.
    Shows built-in and custom types with their configuration."""
    deps = _get_deps()
    registry = deps.get_content_type_registry()
    all_types = await registry.get_all()
    if not all_types:
        return "No content types available."

    parts = ["# Content Types\n"]
    parts.append("| Slug | Name | Mode | Words | Built-in |")
    parts.append("|------|------|------|-------|----------|")
    for slug, config in sorted(all_types.items()):
        builtin = "yes" if config.is_builtin else "no"
        parts.append(f"| {slug} | {config.name} | {config.default_mode} | {config.max_words} | {builtin} |")

    return "\n".join(parts)


@server.tool()
async def manage_content_type(
    action: str,
    slug: str,
    name: str = "",
    default_mode: str = "professional",
    structure_hint: str = "",
    max_words: int = 500,
    description: str = "",
) -> str:
    """Add or remove a content type from the Second Brain.

    Args:
        action: 'add' to create/update a content type, 'remove' to delete it
        slug: Content type slug in kebab-case (e.g., 'newsletter', 'blog-post')
        name: Human-readable name (required for 'add')
        default_mode: Communication mode — casual, professional, or formal
        structure_hint: Composition guide (required for 'add', e.g., 'Hook -> Body -> CTA')
        max_words: Target word count (default 500)
        description: Brief description of the content type
    """
    try:
        slug = _validate_mcp_input(slug, label="slug")
    except ValueError as e:
        return str(e)
    deps = _get_deps()
    registry = deps.get_content_type_registry()

    if action == "add":
        if not name or not structure_hint:
            return "Both 'name' and 'structure_hint' are required for adding a content type."
        row = {
            "slug": slug,
            "name": name,
            "default_mode": default_mode,
            "structure_hint": structure_hint,
            "example_type": slug,
            "max_words": max_words,
            "description": description,
            "is_builtin": False,
        }
        await deps.storage_service.upsert_content_type(row)
        registry.invalidate()
        return f"Added content type '{slug}' ({name})"

    elif action == "remove":
        existing = await deps.storage_service.get_content_type_by_slug(slug)
        if not existing:
            return f"No content type found with slug '{slug}'"
        deleted = await deps.storage_service.delete_content_type(slug)
        if deleted:
            registry.invalidate()
            return f"Removed content type '{slug}'"
        return f"Failed to remove '{slug}'"

    else:
        return f"Unknown action '{action}'. Use 'add' or 'remove'."


@server.tool()
async def vector_search(
    query: str,
    table: str = "memory_content",
    limit: int = 10,
) -> str:
    """Search your Second Brain using vector similarity (pgvector).

    Generates an embedding for the query and finds the most similar content
    in the specified table. Complements semantic search (recall) with
    pure vector similarity matching.

    Args:
        query: Text to search for (generates embedding automatically)
        table: Table to search: memory_content, patterns, examples, knowledge_repo
        limit: Maximum results (default 10)
    """
    try:
        query = _validate_mcp_input(query, label="query")
    except ValueError as e:
        return str(e)

    deps = _get_deps()

    if not deps.embedding_service:
        return "Vector search unavailable: VOYAGE_API_KEY or OPENAI_API_KEY not configured."

    try:
        timeout = deps.config.api_timeout_seconds
        async with asyncio.timeout(timeout):
            embedding = await deps.embedding_service.embed_query(query)
            results = await deps.storage_service.vector_search(
                embedding=embedding,
                table=table,
                limit=limit,
            )
    except TimeoutError:
        return f"Vector search timed out after {timeout}s."
    except ValueError as e:
        return str(e)

    if not results:
        return f"No vector matches found in '{table}'."

    formatted = [f"# Vector Search: {query}\n"]
    for r in results:
        sim = r.get("similarity", 0)
        title = r.get("title", "Untitled")
        content = r.get("content", "")[:200]
        formatted.append(f"- [{sim:.3f}] **{title}**: {content}")
    return "\n".join(formatted)


if __name__ == "__main__":
    server.run()
