"""LearnAgent — extract patterns, insights, and experiences from raw text."""

import logging
from datetime import date

from pydantic_ai import Agent, RunContext

from second_brain.agents.utils import tool_error
from second_brain.deps import BrainDeps
from second_brain.schemas import LearnResult

logger = logging.getLogger(__name__)

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
        return tool_error("search_existing_patterns", e)


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
        parts = [f"Stored new pattern '{name}' (confidence: {confidence}) in registry."]
        # Quality gate: auto-promote to examples if associated review scored high enough
        if source_experience:
            try:
                from second_brain.schemas import QUALITY_GATE_SCORE
                experiences = await ctx.deps.storage_service.get_experiences()
                matching = [e for e in experiences if e.get("name") == source_experience
                            and e.get("review_score") and e["review_score"] >= QUALITY_GATE_SCORE]
                if matching:
                    parts.append(f"Source experience scored {matching[0]['review_score']} — pattern promoted from quality work")
            except Exception:
                logger.debug("Quality gate check failed (non-critical)")
        return "\n".join(parts)
    except Exception as e:
        return tool_error("store_pattern", e)


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
        return tool_error("reinforce_existing_pattern", e)


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
        return tool_error("add_to_memory", e)


@learn_agent.tool
async def store_experience(
    ctx: RunContext[BrainDeps],
    name: str,
    category: str,
    output_summary: str,
    learnings: str,
    patterns_extracted: list[str] | None = None,
    project_id: str | None = None,
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
        if project_id:
            experience_data["project_id"] = project_id
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

        # Store as project artifact if linked to a project
        if project_id:
            try:
                await ctx.deps.storage_service.add_project_artifact({
                    "project_id": project_id,
                    "artifact_type": "learnings",
                    "title": f"Learnings: {name}",
                    "content": learnings,
                    "metadata": {"patterns_extracted": patterns_extracted or []},
                })
            except Exception:
                logger.debug("Project artifact creation failed (non-critical)")

        return f"Recorded experience '{name}' (category: {category})."
    except Exception as e:
        return tool_error("store_experience", e)


@learn_agent.tool
async def learn_from_review(
    ctx: RunContext[BrainDeps],
    review_summary: str,
    review_score: float,
    strengths: str,
    issues: str,
    content_type: str = "",
) -> str:
    """Extract learnings from a review result. Call this after a review to automatically
    learn from what worked (strengths with score 8+) and what didn't (issues)."""
    try:
        parts = [f"Review Score: {review_score}/10"]

        # Record review as experience
        experience = {
            "name": f"review-{content_type or 'unknown'}-{review_score}",
            "category": "content",
            "output_summary": review_summary[:500],
            "review_score": review_score,
            "learnings": f"Strengths: {strengths}\nIssues: {issues}",
        }
        await ctx.deps.storage_service.add_experience(experience)

        # Track growth event
        try:
            await ctx.deps.storage_service.add_growth_event({
                "event_type": "content_reviewed",
                "details": {
                    "score": review_score,
                    "content_type": content_type,
                    "strengths_count": len(strengths.split("\n")),
                    "issues_count": len(issues.split("\n")),
                },
            })
        except Exception:
            logger.debug("Growth event recording failed (non-critical)")

        # If score is high enough, suggest example promotion
        from second_brain.schemas import QUALITY_GATE_SCORE
        if review_score >= QUALITY_GATE_SCORE:
            parts.append(f"Score {review_score} >= {QUALITY_GATE_SCORE} — eligible for example promotion")
            parts.append("Use store_pattern to extract successful patterns from strengths")
        else:
            parts.append(f"Score {review_score} < {QUALITY_GATE_SCORE} — focus on learning from issues")

        if strengths.strip():
            parts.append(f"\nStrengths to learn from:\n{strengths}")
        if issues.strip():
            parts.append(f"\nIssues to address:\n{issues}")

        return "\n".join(parts)
    except Exception as e:
        return tool_error("learn_from_review", e)


@learn_agent.tool
async def consolidate_memories(
    ctx: RunContext[BrainDeps],
    batch_size: int = 10,
    batch_offset: int = 0,
) -> str:
    """Review a batch of accumulated memories for consolidation.

    Call with batch_offset=0 first, then increment by batch_size
    to process all uncategorized memories.

    Args:
        batch_size: Number of memories per batch (default 10).
        batch_offset: Starting offset for pagination.
    """
    try:
        all_memories = await ctx.deps.memory_service.get_all()
        if not all_memories:
            return "No memories found in Mem0. Nothing to consolidate."

        uncategorized = [
            m for m in all_memories
            if m.get("metadata", {}).get("category", "") not in
            ("pattern", "pattern_reinforcement", "graduated")
        ]

        if not uncategorized:
            return "All memories are already categorized. Nothing to consolidate."

        total = len(uncategorized)
        batch = uncategorized[batch_offset:batch_offset + batch_size]

        if not batch:
            return f"No more uncategorized memories. Total checked: {total}."

        min_size = ctx.deps.config.graduation_min_memories

        formatted = [
            f"Batch {batch_offset // batch_size + 1}: "
            f"Showing {len(batch)} of {total} uncategorized memories "
            f"(offset {batch_offset}):\n"
        ]
        for i, mem in enumerate(batch, batch_offset + 1):
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
        formatted.append(
            f"\n---\nNext batch: call with batch_offset={batch_offset + batch_size}"
        )
        return "\n".join(formatted)
    except Exception as e:
        return tool_error("consolidate_memories", e)


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
        return tool_error("tag_graduated_memories", e)
