"""Shared utilities for Second Brain agents."""

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pydantic_ai import Agent
    from pydantic_ai.models import Model

    from second_brain.config import BrainConfig
    from second_brain.deps import BrainDeps

logger = logging.getLogger(__name__)


def format_memories(memories: list[dict], limit: int | None = None) -> str:
    """Format Mem0 search results as markdown list.

    Args:
        memories: Raw Mem0 search results (list of dicts with 'memory'/'result' and 'score').
        limit: Max memories to format. None = all.

    Returns:
        Formatted markdown string with score and content.
    """
    if not memories:
        return ""
    items = memories[:limit] if limit else memories
    lines = []
    for m in items:
        content = m.get("memory", m.get("result", ""))
        score = m.get("rerank_score", m.get("score", 0))
        lines.append(f"- [{score:.2f}] {content}")
    return "\n".join(lines)


def format_relations(relations: list[dict]) -> str:
    """Format graph relationships as markdown list.

    Args:
        relations: Graph relationship dicts with source/relationship/target keys.

    Returns:
        Formatted markdown string. Empty string if no relations.
    """
    if not relations:
        return ""
    lines = ["\n## Graph Relationships"]
    for rel in relations:
        src = rel.get("source", rel.get("entity", "?"))
        relationship = rel.get("relationship", "?")
        tgt = rel.get("target", rel.get("connected_to", "?"))
        lines.append(f"- {src} --[{relationship}]--> {tgt}")
    return "\n".join(lines)


def format_search_result(
    memories: list[dict],
    relations: list[dict],
    memory_limit: int | None = None,
) -> str:
    """Format both memories and relations from a SearchResult.

    Convenience wrapper around format_memories + format_relations for dual-path agents.
    Returns combined formatted string. Either field can be empty.
    """
    parts = []
    mem_text = format_memories(memories, limit=memory_limit)
    if mem_text:
        parts.append(mem_text)
    rel_text = format_relations(relations)
    if rel_text:
        parts.append(rel_text)
    return "\n".join(parts) if parts else ""


# Domain-specific synonym map for query expansion
_QUERY_SYNONYMS: dict[str, list[str]] = {
    "pattern": ["template", "framework", "approach"],
    "client": ["customer", "account", "prospect"],
    "voice": ["tone", "style", "brand voice"],
    "email": ["message", "outreach", "correspondence"],
    "linkedin": ["social", "post", "content"],
    "review": ["feedback", "critique", "score"],
    "project": ["initiative", "engagement", "work"],
    "experience": ["past work", "case study", "example"],
}


def expand_query(query: str, max_expansions: int = 3) -> str:
    """Expand a search query with domain-specific synonyms.

    Zero-latency expansion — no LLM call needed. Appends up to max_expansions
    synonym terms to improve recall for domain-specific vocabulary.

    Args:
        query: Original search query.
        max_expansions: Maximum synonym terms to append.

    Returns:
        Expanded query string. Returns original if no synonyms match.
    """
    tokens = query.lower().split()
    expansions: list[str] = []
    for token in tokens:
        if token in _QUERY_SYNONYMS:
            for syn in _QUERY_SYNONYMS[token]:
                if syn.lower() not in query.lower():
                    expansions.append(syn)
    if expansions:
        return query + " " + " ".join(expansions[:max_expansions])
    return query


def deduplicate_results(
    results: list[dict],
    content_key: str = "memory",
    fallback_key: str = "result",
) -> list[dict]:
    """Remove duplicate results by content hash.

    Used when merging results from multiple sources (Mem0 + Supabase vector +
    Supabase full-text). Preserves the first occurrence and drops later duplicates.

    Args:
        results: List of result dicts from any search source.
        content_key: Primary key for content text.
        fallback_key: Fallback key if primary is missing.

    Returns:
        Deduplicated list preserving original order.
    """
    if not results:
        return results

    import hashlib

    seen: set[str] = set()
    deduped: list[dict] = []
    for r in results:
        content = r.get(content_key, r.get(fallback_key, ""))
        if not content:
            deduped.append(r)
            continue
        content_hash = hashlib.md5(content.encode()).hexdigest()
        if content_hash not in seen:
            seen.add(content_hash)
            deduped.append(r)
    return deduped


def classify_query_complexity(
    query: str,
    word_threshold: int = 8,
) -> str:
    """Classify a query as simple, medium, or complex using heuristics.

    Zero-latency classification — no LLM call needed. Uses word count,
    question structure, and multi-topic indicators to determine retrieval depth.

    Simple: short factual lookups (1-3 words, single topic)
    Medium: topic-based recall (4-threshold words, single topic)
    Complex: synthesis queries (above threshold words, multi-topic, or comparison)

    Args:
        query: The search query string.
        word_threshold: Word count above which queries are classified as complex.

    Returns:
        "simple", "medium", or "complex"
    """
    words = query.split()
    word_count = len(words)
    query_lower = query.lower()

    # Complexity signals
    has_comparison = any(w in query_lower for w in [
        "compare", "contrast", "difference", "versus", "vs",
        "better", "worse", "trade-off", "pros and cons",
    ])
    has_synthesis = any(w in query_lower for w in [
        "synthesize", "combine", "integrate", "across",
        "all", "everything", "comprehensive", "overview",
    ])
    has_multi_topic = " and " in query_lower or " or " in query_lower
    multi_question = query.count("?") > 1

    # Classification
    if word_count <= 3 and not has_comparison and not has_synthesis:
        return "simple"
    if (word_count > word_threshold
            or has_comparison
            or has_synthesis
            or multi_question):
        return "complex"
    return "medium"


def normalize_results(
    results: list[dict],
    source: str,
    content_key: str = "memory",
    score_key: str = "score",
) -> list[dict]:
    """Normalize search results from any source into a canonical format.

    Canonical format: {"memory": str, "score": float, "source": str}
    This enables deduplicate_results() and rerank_memories() to work on
    merged results from Mem0, pgvector, hybrid search, and Graphiti.

    Args:
        results: Raw results from any search source.
        source: Source identifier (e.g., "mem0", "pgvector:patterns", "keyword:memory_content").
        content_key: Key containing the text content in source results.
        score_key: Key containing the relevance score in source results.

    Returns:
        List of normalized dicts with "memory", "score", and "source" keys.
    """
    normalized = []
    for r in results:
        content = r.get(content_key, r.get("memory", r.get("result", r.get("content", ""))))
        score = r.get(score_key, r.get("score", r.get("similarity", r.get("relevance_score", 0))))
        if not content:
            continue
        normalized.append({
            "memory": content,
            "score": float(score) if score else 0.0,
            "source": source,
            # Preserve original dict for metadata access
            "_original": r,
        })
    return normalized


async def parallel_search_gather(
    searches: list[tuple[str, object]],
) -> tuple[list[dict], list[str]]:
    """Run multiple search coroutines in parallel with fault-tolerant error handling.

    Each search source runs independently — individual failures don't abort the gather.
    Failed sources are logged and excluded from results.

    Args:
        searches: List of (source_name, coroutine) tuples.
                 source_name is used for logging and result tagging.

    Returns:
        Tuple of (all_results, source_names):
        - all_results: Flat list of normalized result dicts from all successful sources.
        - source_names: List of source names that contributed results.
    """
    import asyncio as _asyncio

    source_names_input = [name for name, _ in searches]
    coros = [coro for _, coro in searches]

    results = await _asyncio.gather(*coros, return_exceptions=True)

    all_results: list[dict] = []
    contributing_sources: list[str] = []

    for name, result in zip(source_names_input, results):
        if isinstance(result, BaseException):
            logger.debug("Parallel search source '%s' failed: %s", name, result)
            continue
        if isinstance(result, list) and result:
            all_results.extend(result)
            contributing_sources.append(name)
        elif hasattr(result, "memories") and result.memories:
            # Handle SearchResult objects from MemoryService
            all_results.extend(
                normalize_results(result.memories, source=name)
            )
            contributing_sources.append(name)

    return all_results, contributing_sources


async def parallel_multi_table_search(
    deps: "BrainDeps",
    query: str,
    tables: list[str] | None = None,
    limit: int = 10,
) -> tuple[list[dict], list[str]]:
    """Search multiple Supabase tables in parallel via semantic search.

    Medium-complexity path: searches patterns, examples, knowledge, and
    experiences tables concurrently. Requires embedding service.

    Args:
        deps: BrainDeps with embedding_service and storage_service.
        query: Search query string.
        tables: Tables to search. Defaults to all 4 semantic search tables.
        limit: Max results per table.

    Returns:
        Tuple of (normalized_results, contributing_sources).
    """
    if not deps.embedding_service:
        return [], []

    all_tables = tables or ["patterns", "examples", "knowledge", "experiences"]
    embedding = await deps.embedding_service.embed_query(query)

    table_method_map = {
        "patterns": ("search_patterns_semantic", "pgvector:patterns"),
        "examples": ("search_examples_semantic", "pgvector:examples"),
        "knowledge": ("search_knowledge_semantic", "pgvector:knowledge"),
        "experiences": ("search_experiences_semantic", "pgvector:experiences"),
    }

    searches = []
    for table in all_tables:
        if table not in table_method_map:
            continue
        method_name, source_label = table_method_map[table]
        method = getattr(deps.storage_service, method_name, None)
        if method:
            searches.append((
                source_label,
                method(embedding=embedding, limit=limit),
            ))

    if not searches:
        return [], []

    return await parallel_search_gather(searches)


async def search_with_graph_fallback(
    deps: "BrainDeps",
    query: str,
    base_relations: list[dict] | None = None,
) -> list[dict]:
    """Search Graphiti (if available) and merge with base relations.

    Graphiti is optional -- failures are debug-level, non-blocking.

    Args:
        deps: BrainDeps with optional graphiti_service.
        query: Search query string.
        base_relations: Relations already collected (e.g., from Mem0 graph).

    Returns:
        Merged list of relations (base + graphiti results).
    """
    relations = list(base_relations or [])
    if deps.graphiti_service:
        try:
            graphiti_rels = await deps.graphiti_service.search(query)
            relations = relations + graphiti_rels
        except Exception as e:
            logger.debug("Graphiti search failed (non-critical): %s", e)
    return relations


async def rerank_memories(
    deps: "BrainDeps",
    query: str,
    memories: list[dict],
    top_k: int | None = None,
    instruction: str | None = None,
) -> list[dict]:
    """Rerank Mem0 search results using Voyage reranker.

    Graceful degradation: returns original memories if Voyage unavailable.

    Args:
        deps: BrainDeps with optional voyage_service.
        query: Original search query.
        memories: Raw Mem0 results (dicts with 'memory'/'result' key).
        top_k: Max results after reranking. None = config default.

    Returns:
        Reranked list of memory dicts, or original list if reranking unavailable.
    """
    if not deps.voyage_service or not memories:
        return memories

    # Extract text from memory dicts
    documents = [
        m.get("memory", m.get("result", ""))
        for m in memories
    ]
    documents = [d for d in documents if d]  # filter empties

    if not documents:
        return memories

    try:
        if instruction and hasattr(deps.voyage_service, "rerank_with_instructions"):
            reranked = await deps.voyage_service.rerank_with_instructions(
                query, documents, instruction=instruction, top_k=top_k,
            )
        else:
            reranked = await deps.voyage_service.rerank(query, documents, top_k=top_k)
        # Rebuild memory dicts in reranked order
        result = []
        for r in reranked:
            idx = r["index"]
            if idx < len(memories):
                mem = dict(memories[idx])
                mem["rerank_score"] = r["relevance_score"]
                result.append(mem)
        return result
    except Exception as e:
        logger.debug("Reranking failed (non-critical): %s", e)
        return memories


async def run_review_learn_pipeline(
    content: str,
    content_type: str,
    deps: "BrainDeps",
    model: "Model | None",
) -> dict[str, Any]:
    """Run the review->learn pipeline: review content, then learn from the review results.

    Returns dict with 'review' (ReviewResult) and 'learn' (LearnResult) keys.
    """
    from second_brain.agents.review import run_full_review
    from second_brain.agents.learn import learn_agent
    from second_brain.models import get_agent_model

    # Step 1: Review (per-agent model resolution)
    review_model = get_agent_model("review", deps.config) if deps else model
    review_result = await run_full_review(
        content=content,
        content_type=content_type,
        deps=deps,
        model=review_model,
    )

    # Step 2: Learn from review (per-agent model resolution)
    learn_model = get_agent_model("learn", deps.config) if deps else model
    strengths = "\n".join(review_result.top_strengths or [])
    issues = "\n".join(review_result.critical_issues or [])
    overall_score = review_result.overall_score
    summary = review_result.summary or ""

    learn_prompt = (
        f"Learn from this review of {content_type} content.\n"
        f"Review score: {overall_score}/10\n"
        f"Summary: {summary}\n"
        f"Strengths:\n{strengths}\n"
        f"Issues:\n{issues}\n\n"
        f"Extract patterns from what worked well (strengths) and note what to avoid (issues)."
    )

    learn_result = await learn_agent.run(learn_prompt, deps=deps, model=learn_model)

    return {
        "review": review_result,
        "learn": learn_result.output,
    }


def format_pattern_registry(patterns: list[dict[str, Any]], config: "BrainConfig | None" = None) -> str:
    """Format patterns as a registry table for display."""
    if not patterns:
        return "No patterns in registry."

    stale_days = config.stale_pattern_days if config else 30

    lines = ["| Pattern | Topic | Confidence | Uses | Last Updated | Status |",
             "|---------|-------|------------|------|--------------|--------|"]

    from datetime import datetime, timedelta, timezone

    for p in patterns:
        name = p.get("name", "Unknown")
        topic = p.get("topic", "-")
        conf = p.get("confidence", "LOW")
        uses = p.get("use_count", 0)
        updated = p.get("date_updated", "-")
        failures = p.get("consecutive_failures", 0)

        # Determine status
        status = "Active"
        if failures >= 2:
            status = "At Risk"
        elif updated and updated != "-":
            try:
                last = datetime.fromisoformat(updated.replace("Z", "+00:00")) if "T" in updated else datetime.strptime(updated, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if datetime.now(timezone.utc) - last > timedelta(days=stale_days):
                    status = "Stale"
            except (ValueError, TypeError):
                pass

        lines.append(f"| {name} | {topic} | {conf} | {uses} | {updated} | {status} |")

    lines.append(f"\nTotal: {len(patterns)} patterns")
    conf_counts: dict[str, int] = {}
    for p in patterns:
        c = p.get("confidence", "LOW")
        conf_counts[c] = conf_counts.get(c, 0) + 1
    dist = ", ".join(f"{k}: {v}" for k, v in sorted(conf_counts.items()))
    lines.append(f"Distribution: {dist}")

    return "\n".join(lines)


async def run_agent_with_retry(
    agent: "Agent[BrainDeps, Any]",
    prompt: str,
    deps: "BrainDeps",
    model: "Model | None" = None,
    max_attempts: int = 3,
    validate_fn: Callable[..., Any] | None = None,
) -> Any:
    """Run an agent with optional external validation and retry.

    If validate_fn is provided, it receives the agent output and should return
    (True, output) on success or (False, feedback_message) on failure.
    On failure, the agent is re-run with the feedback appended to the prompt.

    This is for cases where @output_validator can't be used (e.g., validation
    requires calling another agent or external service).

    Args:
        agent: Pydantic AI Agent instance.
        prompt: User prompt.
        deps: BrainDeps instance.
        model: Optional model override.
        max_attempts: Maximum retry attempts (default 3).
        validate_fn: Optional async callable(output) -> (bool, str).

    Returns:
        The agent's output (typed per agent's output_type).
    """
    from pydantic_ai.usage import UsageLimits

    limits = UsageLimits(request_limit=deps.config.agent_request_limit)
    kwargs = {"deps": deps, "usage_limits": limits}
    if model is not None:
        kwargs["model"] = model

    last_result = None
    current_prompt = prompt

    for attempt in range(max_attempts):
        result = await agent.run(current_prompt, **kwargs)
        last_result = result.output

        if validate_fn is None:
            return last_result

        is_valid, feedback = await validate_fn(last_result)
        if is_valid:
            return last_result

        # Append feedback and retry
        current_prompt = (
            f"{prompt}\n\n"
            f"[Validation feedback from attempt {attempt + 1}]: {feedback}\n"
            f"Please address this feedback and try again."
        )
        logger.debug(
            "Agent validation failed (attempt %d/%d): %s",
            attempt + 1, max_attempts, feedback,
        )

    # Return last result even if validation failed
    logger.warning("Agent validation exhausted %d attempts", max_attempts)
    return last_result


def get_agent_registry() -> dict:
    """Get the agent registry mapping route names to agent instances.

    Lazy-loaded to avoid circular imports. Each agent module is imported
    only when the registry is first requested.

    Returns:
        Dict mapping AgentRoute string to (agent_instance, description) tuples.
    """
    from second_brain.agents.recall import recall_agent
    from second_brain.agents.ask import ask_agent
    from second_brain.agents.learn import learn_agent
    from second_brain.agents.create import create_agent
    from second_brain.agents.review import review_agent
    from second_brain.agents.chief_of_staff import chief_of_staff  # noqa: F401

    registry = {
        "recall": (recall_agent, "Semantic memory search"),
        "ask": (ask_agent, "Contextual Q&A with brain knowledge"),
        "learn": (learn_agent, "Pattern extraction and learning"),
        "create": (create_agent, "Content creation with voice and patterns"),
        "review": (review_agent, "Single-dimension content review"),
    }

    # Lazily add new agents as they become available
    try:
        from second_brain.agents.clarity import clarity_agent
        registry["clarity"] = (clarity_agent, "Content clarity analysis")
    except ImportError:
        pass
    try:
        from second_brain.agents.synthesizer import synthesizer_agent
        registry["synthesizer"] = (synthesizer_agent, "Feedback consolidation")
    except ImportError:
        pass
    try:
        from second_brain.agents.template_builder import template_builder_agent
        registry["template_builder"] = (template_builder_agent, "Template identification")
    except ImportError:
        pass
    try:
        from second_brain.agents.coach import coach_agent
        registry["coach"] = (coach_agent, "Daily accountability coaching")
    except ImportError:
        pass
    try:
        from second_brain.agents.pmo import pmo_agent
        registry["pmo"] = (pmo_agent, "Priority advisory")
    except ImportError:
        pass
    try:
        from second_brain.agents.email_agent import email_agent
        registry["email"] = (email_agent, "Email operations")
    except ImportError:
        pass
    try:
        from second_brain.agents.specialist import specialist_agent
        registry["specialist"] = (specialist_agent, "Claude Code expertise")
    except ImportError:
        pass

    return registry


async def run_pipeline(
    steps: list[str],
    initial_prompt: str,
    deps: "BrainDeps",
    model: "Model | None" = None,
    content_type: str | None = None,
) -> dict[str, Any]:
    """Run a multi-agent pipeline, chaining results between agents.

    Each step's output is formatted and prepended to the next step's prompt.
    Special handling for 'review' step (uses run_full_review).

    Args:
        steps: Ordered list of AgentRoute names (e.g., ["recall", "create", "review"])
        initial_prompt: The user's original request
        deps: BrainDeps instance
        model: Optional model override
        content_type: Content type for create/review steps

    Returns:
        Dict mapping step name to its output, plus "final" key with last step's output.
    """
    from pydantic_ai.usage import UsageLimits

    registry = get_agent_registry()
    limits = UsageLimits(request_limit=deps.config.pipeline_request_limit)
    results = {}
    current_context = initial_prompt

    for i, step_name in enumerate(steps):
        if step_name not in registry:
            logger.warning("Pipeline step '%s' not in registry, skipping", step_name)
            continue

        agent, description = registry[step_name]
        logger.info("Pipeline step %d/%d: %s (%s)", i + 1, len(steps), step_name, description)

        try:
            # Per-step model resolution
            from second_brain.models import get_agent_model
            step_model = get_agent_model(step_name, deps.config) if deps else model

            # Special handling for review — uses run_full_review()
            if step_name == "review":
                from second_brain.agents.review import run_full_review
                # Use previous step's output as content to review
                content_to_review = current_context
                if "create" in results:
                    content_to_review = str(results["create"])
                review_result = await run_full_review(
                    content=content_to_review,
                    deps=deps,
                    model=step_model,
                    content_type=content_type,
                )
                results[step_name] = review_result
                current_context = (
                    f"{current_context}\n\n"
                    f"[Review result]: Score {review_result.overall_score}/10 — "
                    f"{review_result.verdict}\n"
                    f"Strengths: {', '.join(review_result.top_strengths[:3])}\n"
                    f"Issues: {', '.join(review_result.critical_issues[:3])}"
                )
                continue

            # Standard agent execution
            kwargs = {"deps": deps, "usage_limits": limits}
            if step_model is not None:
                kwargs["model"] = step_model

            result = await agent.run(current_context, **kwargs)
            results[step_name] = result.output

            # Build context for next step
            output_str = str(result.output)
            if hasattr(result.output, "summary") and result.output.summary:
                output_str = result.output.summary
            elif hasattr(result.output, "draft") and result.output.draft:
                output_str = result.output.draft
            elif hasattr(result.output, "answer") and result.output.answer:
                output_str = result.output.answer

            current_context = (
                f"{initial_prompt}\n\n"
                f"[Context from {step_name}]: {output_str}"
            )

        except Exception as e:
            logger.error("Pipeline step '%s' failed: %s", step_name, e)
            results[step_name] = {"error": str(e)}
            # Continue pipeline — don't block remaining steps

    results["final"] = results.get(steps[-1], None) if steps else None
    return results


async def load_voice_context(
    deps: "BrainDeps",
    preview_limit: int | None = None,
    include_graph: bool = False,
) -> str:
    """Load user's voice/tone guide from storage. Shared across agents.

    Args:
        deps: BrainDeps with storage_service
        preview_limit: Max chars per content item (None = use config default)
        include_graph: Whether to enrich with graph relationships
    """
    limit = preview_limit or deps.config.content_preview_limit
    content = await deps.storage_service.get_memory_content("style-voice")
    if not content:
        return "No voice guide found. Write in a clear, direct, conversational tone."
    sections = []
    for item in content:
        title = item.get("title", "Untitled")
        text = item.get("content", "")[:limit]
        sections.append(f"### {title}\n{text}")
    if include_graph:
        graphiti_rels = await search_with_graph_fallback(deps, "voice tone style brand")
        if graphiti_rels:
            sections.append("\n### Graph Context")
            rel_text = format_relations(graphiti_rels)
            if rel_text:
                sections.append(rel_text)
    return "## Voice & Tone Guide\n" + "\n\n".join(sections)


def tool_error(tool_name: str, error: Exception) -> str:
    """Standard error format for agent tool failures.

    Returns a user-friendly error string. Logs the technical details.

    Args:
        tool_name: Name of the tool that failed.
        error: The exception that occurred.

    Returns:
        Formatted error string for the LLM.
    """
    logger.warning("%s failed: %s", tool_name, type(error).__name__)
    logger.debug("%s error detail: %s", tool_name, error)
    return f"{tool_name} unavailable: {type(error).__name__}"
