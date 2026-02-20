"""Shared utilities for Second Brain agents."""

import asyncio
import hashlib
import logging
import time as _time
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
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
        score = float(m.get("rerank_score", m.get("score", 0)) or 0)
        line = f"- [{score:.2f}] {content}"
        source = m.get("source", "")
        if source:
            line = f"{line} [{source}]"
        lines.append(line)
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
    query_lower = query.lower()
    tokens = query_lower.split()
    expansions: list[str] = []
    for token in tokens:
        if token in _QUERY_SYNONYMS:
            for syn in _QUERY_SYNONYMS[token]:
                if syn.lower() not in query_lower:
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

    seen: set[str] = set()
    deduped: list[dict] = []
    for r in results:
        content = r.get(content_key, r.get(fallback_key, ""))
        if not content:
            deduped.append(r)
            continue
        content_hash = hashlib.sha256(content.encode(), usedforsecurity=False).hexdigest()
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


_CONVERSATIONAL_TOKENS: set[str] = {
    # Greetings
    "hello", "hi", "hey", "howdy", "hola", "yo", "sup",
    "good morning", "good afternoon", "good evening", "good night",
    # Farewells
    "bye", "goodbye", "see you", "later", "cya", "peace",
    # Gratitude
    "thanks", "thank you", "thx", "ty", "cheers", "appreciate it",
    # Affirmations
    "ok", "okay", "sure", "yep", "yup", "yeah", "yes", "no", "nope",
    # Small talk
    "lol", "haha", "hehe", "lmao", "rofl", "nice", "cool", "awesome",
    "wow", "omg", "whoa",
    # Pleasantries
    "how are you", "what's up", "whats up", "how's it going",
    "how do you do", "nice to meet you",
}

_GREETING_STARTS: set[str] = {
    "hi", "hey", "hello", "yo", "sup", "howdy", "hola",
    "morning", "evening", "afternoon", "night",
    "bye", "goodbye", "thanks", "thank",
}


def is_conversational(query: str) -> bool:
    """Detect greetings, small talk, and conversational queries.

    Zero-latency heuristic — no LLM call needed. Used to short-circuit
    expensive memory search tools when the user is just saying hello.

    Args:
        query: The user's input query.

    Returns:
        True if the query is conversational (greeting, small talk, etc.)
    """
    cleaned = query.strip()
    if not cleaned:
        return False

    # Lowercase and strip trailing punctuation
    cleaned_lower = cleaned.lower().rstrip(".!?")

    # Check if all characters are non-ASCII (emoji-only string)
    if cleaned_lower and all(ord(c) > 127 or c == " " for c in cleaned_lower):
        return True

    # Exact match against known conversational tokens
    if cleaned_lower in _CONVERSATIONAL_TOKENS:
        return True

    # Short query starting with a greeting word (e.g., "Hi there", "Hey buddy")
    words = cleaned_lower.split()
    if len(words) <= 4 and words[0] in _GREETING_STARTS:
        # Check none of the other words indicate a real question
        substantive_signals = {"help", "write", "search", "find", "what", "how", "why",
                               "when", "where", "who", "can", "could", "would", "should",
                               "tell", "show", "explain", "create", "draft", "review",
                               "recall", "remember", "pattern", "project", "content",
                               "email", "plan", "need", "want"}
        if not any(w in substantive_signals for w in words[1:]):
            return True

    return False


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
    searches: list[tuple[str, Awaitable[Any]]],
    per_source_timeout: float | None = None,
) -> tuple[list[dict], list[str]]:
    """Run multiple search coroutines in parallel with fault-tolerant error handling.

    Each search source runs independently — individual failures don't abort the gather.
    Failed sources are logged and excluded from results.

    Args:
        searches: List of (source_name, coroutine) tuples.
                 source_name is used for logging and result tagging.
        per_source_timeout: Optional timeout in seconds for each individual source.
                           If a source exceeds this, it's treated as a failed source.

    Returns:
        Tuple of (all_results, source_names):
        - all_results: Flat list of normalized result dicts from all successful sources.
        - source_names: List of source names that contributed results.
    """
    source_names_input = [name for name, _ in searches]
    coros = []
    for _, coro in searches:
        if per_source_timeout is not None:
            coros.append(asyncio.wait_for(coro, timeout=per_source_timeout))
        else:
            coros.append(coro)

    start = _time.perf_counter()
    results = await asyncio.gather(*coros, return_exceptions=True)
    total_ms = (_time.perf_counter() - start) * 1000

    all_results: list[dict] = []
    contributing_sources: list[str] = []
    source_timings: list[str] = []

    for name, result in zip(source_names_input, results):
        if isinstance(result, BaseException):
            if isinstance(result, asyncio.TimeoutError):
                logger.info("Search source '%s' timed out", name)
            else:
                logger.info("Search source '%s' failed: %s", name, type(result).__name__)
            source_timings.append(f"{name}=FAIL")
            continue
        if isinstance(result, list) and result:
            all_results.extend(
                normalize_results(result, source=name,
                                  content_key="content", score_key="similarity")
            )
            contributing_sources.append(name)
            source_timings.append(f"{name}={len(result)}hits")
        elif hasattr(result, "memories") and result.memories:
            # Handle SearchResult objects from MemoryService
            all_results.extend(
                normalize_results(result.memories, source=name)
            )
            contributing_sources.append(name)
            source_timings.append(f"{name}={len(result.memories)}hits")
        else:
            source_timings.append(f"{name}=0hits")

    logger.info(
        "parallel_search_gather: %.0fms total, sources=[%s]",
        total_ms, ", ".join(source_timings),
    )

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

    return await parallel_search_gather(
        searches,
        per_source_timeout=deps.config.service_timeout_seconds,
    )


async def deep_recall_search(
    deps: "BrainDeps",
    query: str,
    limit: int = 10,
) -> dict[str, Any]:
    """Deep parallel recall — fans out to ALL search sources concurrently.

    Complex query path: runs Mem0 semantic + hybrid pgvector +
    4 table-specific semantic searches + optional Graphiti in parallel.
    Results are normalized, deduplicated, and reranked.

    Args:
        deps: BrainDeps with all services.
        query: Complex search query.
        limit: Max final results after reranking.

    Returns:
        Dict with keys: memories (list[dict]), relations (list[dict]),
        search_sources (list[str]), query (str).
    """


    expanded = expand_query(query)
    oversample = deps.config.retrieval_oversample_factor
    search_limit = limit * oversample

    # --- Build all search coroutines ---
    searches: list[tuple[str, Awaitable[Any]]] = []

    # 1. Mem0 semantic search
    searches.append(("mem0", deps.memory_service.search(expanded, limit=search_limit)))

    # 2. Hybrid pgvector search (if embedding available)
    embedding = None
    if deps.embedding_service:
        try:
            embedding = await deps.embedding_service.embed_query(query)
        except Exception as e:
            logger.warning("Embedding failed in deep_recall_search (non-fatal): %s", type(e).__name__)
            logger.debug("Embedding error detail: %s", e)

    if embedding:
        searches.append((
            "hybrid:memory_content",
            deps.storage_service.hybrid_search(
                query_text=query,
                query_embedding=embedding,
                table="memory_content",
                limit=search_limit,
            ),
        ))

        # 3. Table-specific semantic searches
        for table, method_name in [
            ("patterns", "search_patterns_semantic"),
            ("examples", "search_examples_semantic"),
            ("knowledge", "search_knowledge_semantic"),
            ("experiences", "search_experiences_semantic"),
        ]:
            method = getattr(deps.storage_service, method_name, None)
            if method:
                searches.append((
                    f"pgvector:{table}",
                    method(embedding=embedding, limit=search_limit),
                ))

    # 4. Optional Graphiti graph search
    if deps.graphiti_service:
        searches.append(("graphiti", deps.graphiti_service.search(query)))

    # --- Execute all searches in parallel (with per-source timeout) ---
    source_names = [name for name, _ in searches]
    per_source_timeout = deps.config.service_timeout_seconds
    coros = [
        asyncio.wait_for(coro, timeout=per_source_timeout)
        for _, coro in searches
    ]
    raw_results = await asyncio.gather(*coros, return_exceptions=True)

    # --- Process results ---
    all_memories: list[dict] = []
    all_relations: list[dict] = []
    contributing_sources: list[str] = []

    for name, result in zip(source_names, raw_results):
        if isinstance(result, BaseException):
            logger.debug("Deep recall source '%s' failed: %s", name, result)
            continue

        # Handle SearchResult (from Mem0)
        if hasattr(result, "memories"):
            if result.memories:
                all_memories.extend(normalize_results(result.memories, source=name))
                contributing_sources.append(name)
            if hasattr(result, "relations") and result.relations:
                all_relations.extend(result.relations)
            continue

        # Handle list[dict] (from Supabase / hybrid)
        if isinstance(result, list) and result:
            if name == "graphiti":
                all_relations.extend(result)
                contributing_sources.append(name)
            else:
                all_memories.extend(
                    normalize_results(result, source=name,
                                      content_key="content", score_key="similarity")
                )
                contributing_sources.append(name)

    # --- Deduplicate and rerank ---
    all_memories = deduplicate_results(all_memories)
    memories = await rerank_memories(deps, query, all_memories, top_k=limit)

    return {
        "memories": memories,
        "relations": all_relations,
        "search_sources": contributing_sources,
        "query": query,
    }


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

    if top_k is None:
        top_k = getattr(deps.config, "voyage_rerank_top_k", None)

    # Extract text from memory dicts — track original indices
    indexed_docs = []
    for i, m in enumerate(memories):
        text = m.get("memory", m.get("result", ""))
        if text:
            indexed_docs.append((i, text))

    if not indexed_docs:
        return memories

    documents = [text for _, text in indexed_docs]
    original_indices = [idx for idx, _ in indexed_docs]

    try:
        if instruction and hasattr(deps.voyage_service, "rerank_with_instructions"):
            reranked = await deps.voyage_service.rerank_with_instructions(
                query, documents, instruction=instruction, top_k=top_k,
            )
        else:
            reranked = await deps.voyage_service.rerank(query, documents, top_k=top_k)
        # Rebuild memory dicts in reranked order using original index mapping
        result = []
        for r in reranked:
            ridx = r["index"]
            if ridx < len(original_indices):
                orig_idx = original_indices[ridx]
                mem = dict(memories[orig_idx])
                mem["rerank_score"] = r["relevance_score"]
                result.append(mem)
        return result
    except Exception as e:
        logger.debug("Reranking failed (non-critical): %s", e)
        return memories


def format_pattern_registry(patterns: list[dict[str, Any]], config: "BrainConfig | None" = None) -> str:
    """Format patterns as a registry table for display."""
    if not patterns:
        return "No patterns in registry."

    stale_days = config.stale_pattern_days if config else 30

    lines = ["| Pattern | Topic | Confidence | Uses | Last Updated | Status |",
             "|---------|-------|------------|------|--------------|--------|"]

    now = datetime.now(timezone.utc)
    stale_cutoff = now - timedelta(days=stale_days)
    conf_counts: dict[str, int] = {}

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
                if last < stale_cutoff:
                    status = "Stale"
            except (ValueError, TypeError):
                pass

        conf_counts[conf] = conf_counts.get(conf, 0) + 1
        lines.append(f"| {name} | {topic} | {conf} | {uses} | {updated} | {status} |")

    lines.append(f"\nTotal: {len(patterns)} patterns")
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

    from second_brain.agents.registry import get_agent_registry
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

        step_timeout = deps.config.api_timeout_seconds
        if step_name == "review":
            step_timeout *= deps.config.mcp_review_timeout_multiplier
        try:
            async with asyncio.timeout(step_timeout):
                # Per-step model resolution
                from second_brain.models import get_agent_model
                step_model = get_agent_model(step_name, deps.config)

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

        except TimeoutError:
            logger.error("Pipeline step '%s' timed out after %ss", step_name, step_timeout)
            results[step_name] = {"error": f"Step timed out after {step_timeout}s"}
        except Exception as e:
            logger.error("Pipeline step '%s' failed: %s", step_name, type(e).__name__)
            logger.debug("Pipeline step '%s' error detail: %s", step_name, e)
            results[step_name] = {"error": f"Step failed: {type(e).__name__}"}
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


# Prefix used by output validators to detect tool-level backend failures.
TOOL_ERROR_PREFIX = "BACKEND_ERROR:"


def tool_error(tool_name: str, error: Exception) -> str:
    """Standard error format for agent tool failures.

    Returns a prefixed error string. The BACKEND_ERROR: prefix allows output
    validators to deterministically detect service failures without relying
    on LLM instruction-following.

    Args:
        tool_name: Name of the tool that failed.
        error: The exception that occurred.

    Returns:
        Formatted error string for the LLM.
    """
    logger.warning("%s failed: %s", tool_name, type(error).__name__)
    logger.debug("%s error detail: %s", tool_name, error)
    return f"{TOOL_ERROR_PREFIX} {tool_name} unavailable: {type(error).__name__}"
