"""LearnAgent — extract patterns, insights, and experiences from raw text."""

import logging
from datetime import date

from pydantic_ai import Agent, RunContext

logger = logging.getLogger(__name__)

from second_brain.deps import BrainDeps
from second_brain.schemas import LearnResult

# NOTE: When using ClaudeSDKModel (subscription auth), Pydantic AI tools
# are NOT called. Instead, the SDK process calls service MCP tools directly.
# The agent instructions and output schema validation still apply.
learn_agent = Agent(
    deps_type=BrainDeps,
    output_type=LearnResult,
    instructions=(
        "You are a learning extraction agent for an AI Second Brain. "
        "Your job: analyze raw text from work sessions and extract structured learnings. "
        "ALWAYS search for existing patterns first to avoid duplicates. "
        "If an input reinforces an existing pattern, mark is_reinforcement=True and "
        "use the reinforce_existing_pattern tool, NOT store_pattern. "
        "Only use store_pattern for genuinely new patterns. "
        "Confidence rules: LOW (new, 1st use), MEDIUM (2-4 uses), HIGH (5+ uses). "
        "Extract anti-patterns when the input describes what NOT to do. "
        "Store every extracted pattern and add key learnings to semantic memory. "
        "Create an experience entry if the input describes a complete work session with outcomes. "
        "When creating patterns, consider which content types they apply to. "
        "Set applicable_content_types to a list of slugs (e.g., ['linkedin', 'email']) "
        "if the pattern is specific to certain types. Leave it as None for universal patterns."
    ),
)


@learn_agent.instructions
async def inject_existing_patterns(ctx: RunContext[BrainDeps]) -> str:
    """Inject existing pattern names to prevent duplicate extraction."""
    patterns = await ctx.deps.storage_service.get_patterns()
    if not patterns:
        return "No existing patterns in the brain yet. All extractions will be new."
    names = [p["name"] for p in patterns[:ctx.deps.config.pattern_context_limit]]
    return (
        f"Existing patterns (check for reinforcement before creating new): "
        f"{', '.join(names)}"
    )


@learn_agent.tool
async def search_existing_patterns(
    ctx: RunContext[BrainDeps], query: str
) -> str:
    """Search for existing patterns that might match what you're about to extract.
    Call this BEFORE creating new patterns to check for reinforcement opportunities."""
    try:
        patterns = await ctx.deps.storage_service.get_patterns()
        if not patterns:
            return "No existing patterns found. Safe to create new ones."
        matching = [
            p for p in patterns
            if query.lower() in p.get("name", "").lower()
            or query.lower() in p.get("pattern_text", "").lower()
        ]
        if not matching:
            return f"No patterns matching '{query}'. This appears to be a new pattern."
        formatted = []
        for p in matching:
            formatted.append(
                f"- {p['name']} (confidence: {p.get('confidence', 'LOW')}, "
                f"uses: {p.get('use_count', 1)})"
            )
        return f"Existing matches:\n" + "\n".join(formatted)
    except Exception as e:
        logger.warning("search_existing_patterns failed: %s", type(e).__name__)
        return f"Pattern search unavailable: {type(e).__name__}"


@learn_agent.tool
async def store_pattern(
    ctx: RunContext[BrainDeps],
    name: str,
    topic: str,
    pattern_text: str,
    confidence: str = "LOW",
    evidence: list[str] | None = None,
    anti_patterns: list[str] | None = None,
    context: str = "",
    source_experience: str = "",
    applicable_content_types: list[str] | None = None,
) -> str:
    """Store a NEW pattern in the Supabase pattern registry.
    Only use for genuinely new patterns. For reinforcement, use reinforce_existing_pattern.

    Args:
        applicable_content_types: Optional list of content type slugs this pattern
            applies to (e.g., ['linkedin', 'email']). None = universal pattern.
    """
    try:
        existing = await ctx.deps.storage_service.get_pattern_by_name(name)
        if existing:
            return (
                f"Pattern '{name}' already exists (use_count: {existing.get('use_count', 1)}, "
                f"confidence: {existing.get('confidence', 'LOW')}). "
                f"Use reinforce_existing_pattern instead."
            )
        pattern_data = {
            "name": name,
            "topic": topic,
            "pattern_text": pattern_text,
            "confidence": confidence,
            "evidence": evidence or [],
            "anti_patterns": anti_patterns or [],
            "context": context,
            "source_experience": source_experience,
            "applicable_content_types": applicable_content_types,
            "date_updated": str(date.today()),
        }
        try:
            await ctx.deps.storage_service.insert_pattern(pattern_data)
            # Record growth event (non-critical)
            try:
                await ctx.deps.storage_service.add_growth_event({
                    "event_type": "pattern_created",
                    "pattern_name": name,
                    "pattern_topic": topic,
                    "details": {
                        "confidence": confidence,
                        "evidence_count": len(evidence or []),
                    },
                })
            except Exception:
                logger.debug("Failed to record growth event for pattern '%s'", name)
            # Dual-write: sync pattern to Mem0 for semantic discovery (non-critical)
            try:
                mem0_content = f"Pattern: {name} — {pattern_text}"
                if context:
                    mem0_content += f". Context: {context}"
                if applicable_content_types:
                    mem0_content += f". Applies to: {', '.join(applicable_content_types)}"
                await ctx.deps.memory_service.add_with_metadata(
                    content=mem0_content,
                    metadata={
                        "category": "pattern",
                        "pattern_name": name,
                        "topic": topic,
                        "confidence": confidence,
                        "applicable_content_types": applicable_content_types,
                    },
                    enable_graph=True,
                )
            except Exception:
                logger.debug("Failed to sync pattern '%s' to Mem0 (non-critical)", name)
            # Dual-write: add episode to Graphiti for entity extraction (non-critical)
            if ctx.deps.graphiti_service:
                try:
                    graphiti_content = (
                        f"New pattern discovered: {name}. "
                        f"Topic: {topic}. "
                        f"Pattern: {pattern_text}"
                    )
                    if context:
                        graphiti_content += f". Context: {context}"
                    if evidence:
                        graphiti_content += f". Evidence: {'; '.join(evidence[:3])}"
                    await ctx.deps.graphiti_service.add_episode(
                        graphiti_content,
                        metadata={
                            "source": "learn_agent",
                            "category": "pattern",
                            "pattern_name": name,
                            "topic": topic,
                        },
                    )
                except Exception:
                    logger.debug("Failed to sync pattern '%s' to Graphiti (non-critical)", name)
        except Exception as e:
            logger.exception("Failed to insert pattern '%s'", name)
            return f"Error storing pattern '{name}': {e}"
        return f"Stored new pattern '{name}' (confidence: {confidence}) in registry."
    except Exception as e:
        logger.warning("store_pattern failed: %s", type(e).__name__)
        return f"Pattern storage unavailable: {type(e).__name__}"


@learn_agent.tool
async def reinforce_existing_pattern(
    ctx: RunContext[BrainDeps],
    pattern_name: str,
    new_evidence: list[str] | None = None,
) -> str:
    """Reinforce an existing pattern: increment use_count, upgrade confidence, append evidence.
    Use this when is_reinforcement=True instead of store_pattern."""
    try:
        pattern = await ctx.deps.storage_service.get_pattern_by_name(pattern_name)
        if not pattern:
            return (
                f"No existing pattern named '{pattern_name}'. "
                f"Use store_pattern to create it instead."
            )
        try:
            updated = await ctx.deps.storage_service.reinforce_pattern(
                pattern["id"], new_evidence
            )
        except ValueError as e:
            logger.exception("Failed to reinforce pattern '%s'", pattern_name)
            return f"Error reinforcing pattern '{pattern_name}': {e}"
        # Record growth event (non-critical)
        try:
            old_confidence = pattern.get("confidence", "LOW")
            new_confidence = updated.get("confidence", old_confidence)
            await ctx.deps.storage_service.add_growth_event({
                "event_type": "pattern_reinforced",
                "pattern_name": pattern_name,
                "pattern_topic": pattern.get("topic", ""),
                "details": {
                    "new_use_count": updated.get("use_count", 0),
                    "old_confidence": old_confidence,
                    "new_confidence": new_confidence,
                },
            })
            # Record confidence transition if confidence changed
            if new_confidence != old_confidence:
                await ctx.deps.storage_service.add_growth_event({
                    "event_type": "confidence_upgraded",
                    "pattern_name": pattern_name,
                    "pattern_topic": pattern.get("topic", ""),
                    "details": {
                        "from": old_confidence,
                        "to": new_confidence,
                        "use_count": updated.get("use_count", 0),
                    },
                })
                await ctx.deps.storage_service.add_confidence_transition({
                    "pattern_name": pattern_name,
                    "pattern_topic": pattern.get("topic", ""),
                    "from_confidence": old_confidence,
                    "to_confidence": new_confidence,
                    "use_count": updated.get("use_count", 0),
                    "reason": f"Reinforced to use_count {updated.get('use_count', 0)}",
                })
        except Exception:
            logger.debug("Failed to record growth/confidence events for '%s'", pattern_name)
        # Dual-write: update pattern in Mem0 with new confidence (non-critical)
        try:
            mem0_content = (
                f"Pattern reinforced: {pattern_name} — "
                f"now at use_count {updated.get('use_count', 0)}, "
                f"confidence {updated.get('confidence', 'LOW')}"
            )
            await ctx.deps.memory_service.add_with_metadata(
                content=mem0_content,
                metadata={
                    "category": "pattern_reinforcement",
                    "pattern_name": pattern_name,
                    "topic": pattern.get("topic", ""),
                    "confidence": updated.get("confidence", "LOW"),
                },
            )
        except Exception:
            logger.debug("Failed to sync reinforcement for '%s' to Mem0 (non-critical)", pattern_name)
        # Dual-write: add reinforcement episode to Graphiti (non-critical)
        if ctx.deps.graphiti_service:
            try:
                graphiti_content = (
                    f"Pattern reinforced: {pattern_name}. "
                    f"New use_count: {updated.get('use_count', 0)}. "
                    f"Confidence: {updated.get('confidence', 'LOW')}"
                )
                if new_evidence:
                    graphiti_content += f". New evidence: {'; '.join(new_evidence[:3])}"
                await ctx.deps.graphiti_service.add_episode(
                    graphiti_content,
                    metadata={
                        "source": "learn_agent",
                        "category": "pattern_reinforcement",
                        "pattern_name": pattern_name,
                    },
                )
            except Exception:
                logger.debug("Failed to sync reinforcement '%s' to Graphiti (non-critical)", pattern_name)
        return (
            f"Reinforced pattern '{pattern_name}' → "
            f"use_count: {updated['use_count']}, confidence: {updated['confidence']}"
        )
    except Exception as e:
        logger.warning("reinforce_existing_pattern failed: %s", type(e).__name__)
        return f"Pattern reinforcement unavailable: {type(e).__name__}"


@learn_agent.tool
async def add_to_memory(
    ctx: RunContext[BrainDeps],
    content: str,
    category: str = "learning",
) -> str:
    """Store a key learning or insight in Mem0 semantic memory for future recall.
    Use for insights that don't fit a structured pattern format."""
    try:
        metadata = {"category": category, "source": "learn_agent"}
        await ctx.deps.memory_service.add(content, metadata=metadata)
        return f"Added to semantic memory (category: {category})."
    except Exception as e:
        logger.warning("add_to_memory failed: %s", type(e).__name__)
        return f"Memory storage unavailable: {type(e).__name__}"


@learn_agent.tool
async def store_experience(
    ctx: RunContext[BrainDeps],
    name: str,
    category: str,
    output_summary: str,
    learnings: str,
    patterns_extracted: list[str] | None = None,
) -> str:
    """Store a work experience entry in Supabase. Only call this if the input
    describes a complete work session with clear outcomes."""
    try:
        experience_data = {
            "name": name,
            "category": category,
            "output_summary": output_summary,
            "learnings": learnings,
            "patterns_extracted": patterns_extracted or [],
        }
        await ctx.deps.storage_service.add_experience(experience_data)

        # Dual-write: sync experience to Mem0 for graph relationships (non-critical)
        try:
            mem0_content = f"Experience: {name} (category: {category}). {output_summary}"
            if patterns_extracted:
                mem0_content += f". Patterns used: {', '.join(patterns_extracted)}"
            await ctx.deps.memory_service.add_with_metadata(
                content=mem0_content,
                metadata={
                    "category": "experience",
                    "experience_name": name,
                    "experience_category": category,
                },
                enable_graph=True,
            )
        except Exception:
            logger.debug("Failed to sync experience '%s' to Mem0 (non-critical)", name)

        # Dual-write: add experience episode to Graphiti (non-critical)
        if ctx.deps.graphiti_service:
            try:
                graphiti_content = (
                    f"Work experience: {name}. "
                    f"Category: {category}. "
                    f"Output: {output_summary}"
                )
                if learnings:
                    graphiti_content += f". Learnings: {learnings[:500]}"
                if patterns_extracted:
                    graphiti_content += f". Patterns used: {', '.join(patterns_extracted)}"
                await ctx.deps.graphiti_service.add_episode(
                    graphiti_content,
                    metadata={
                        "source": "learn_agent",
                        "category": "experience",
                        "experience_name": name,
                        "experience_category": category,
                    },
                )
            except Exception:
                logger.debug("Failed to sync experience '%s' to Graphiti (non-critical)", name)

        return f"Recorded experience '{name}' (category: {category})."
    except Exception as e:
        logger.warning("store_experience failed: %s", type(e).__name__)
        return f"Experience storage unavailable: {type(e).__name__}"


@learn_agent.tool
async def consolidate_memories(
    ctx: RunContext[BrainDeps],
    min_cluster_size: int | None = None,
) -> str:
    """Review accumulated Mem0 memories and identify recurring themes
    that could become patterns. Returns a summary of memory clusters.

    After reviewing, use store_pattern for new themes and
    reinforce_existing_pattern for themes matching existing patterns.

    Args:
        min_cluster_size: Minimum memories in a cluster to suggest graduation.
            Defaults to config.graduation_min_memories (3).
    """
    try:
        min_size = min_cluster_size or ctx.deps.config.graduation_min_memories

        # Fetch all memories
        all_memories = await ctx.deps.memory_service.get_all()
        if not all_memories:
            return "No memories found in Mem0. Nothing to consolidate."

        # Filter out already-categorized memories (patterns, graduated)
        uncategorized = []
        for mem in all_memories:
            metadata = mem.get("metadata", {})
            category = metadata.get("category", "")
            if category not in ("pattern", "pattern_reinforcement", "graduated"):
                uncategorized.append(mem)

        if not uncategorized:
            return "All memories are already categorized. Nothing to consolidate."

        # Format memories for LLM analysis
        formatted = [f"Found {len(uncategorized)} uncategorized memories (of {len(all_memories)} total):\n"]
        for i, mem in enumerate(uncategorized[:50], 1):  # Limit to 50 for context
            memory_text = mem.get("memory", mem.get("result", ""))
            metadata = mem.get("metadata", {})
            category = metadata.get("category", "uncategorized")
            formatted.append(f"{i}. [{category}] {memory_text}")

        formatted.append(f"\n---\nMinimum cluster size for graduation: {min_size}")
        formatted.append(
            f"Analyze these memories for recurring themes. For each theme "
            f"appearing in {min_size}+ memories:\n"
            "1. Check if it matches an existing pattern (use search_existing_patterns)\n"
            "2. If match: use reinforce_existing_pattern\n"
            "3. If new: use store_pattern to create it\n"
            "Report what you found and what actions you took."
        )

        return "\n".join(formatted)
    except Exception as e:
        logger.warning("consolidate_memories failed: %s", type(e).__name__)
        return f"Memory consolidation unavailable: {type(e).__name__}"


@learn_agent.tool
async def tag_graduated_memories(
    ctx: RunContext[BrainDeps],
    memory_ids: list[str],
    pattern_name: str,
) -> str:
    """Tag memories as graduated after they've been promoted to a pattern.
    This prevents re-processing in future consolidation runs.

    Args:
        memory_ids: List of Mem0 memory IDs to tag.
        pattern_name: Name of the pattern they graduated into.
    """
    try:
        tagged = 0
        for memory_id in memory_ids:
            try:
                await ctx.deps.memory_service.update_memory(
                    memory_id=memory_id,
                    metadata={
                        "category": "graduated",
                        "graduated_to_pattern": pattern_name,
                    },
                )
                tagged += 1
            except Exception as e:
                logger.debug("Failed to tag memory %s as graduated: %s", memory_id, e)

        return f"Tagged {tagged}/{len(memory_ids)} memories as graduated to pattern '{pattern_name}'."
    except Exception as e:
        logger.warning("tag_graduated_memories failed: %s", type(e).__name__)
        return f"Memory tagging unavailable: {type(e).__name__}"
