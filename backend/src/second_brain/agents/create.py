"""CreateAgent — content creation using brain knowledge."""

import logging

from pydantic_ai import Agent, ModelRetry, RunContext

from second_brain.agents.utils import (
    format_memories,
    format_relations,
    load_voice_context,
    rerank_memories,
    search_with_graph_fallback,
    tool_error,
)
from second_brain.deps import BrainDeps
from second_brain.schemas import CreateResult

logger = logging.getLogger(__name__)

# NOTE: When using ClaudeSDKModel (subscription auth), Pydantic AI tools
# are NOT called. Instead, the SDK process calls service MCP tools directly.
# The agent instructions and output schema validation still apply.
create_agent = Agent(
    deps_type=BrainDeps,
    output_type=CreateResult,
    retries=3,
    instructions=(
        "You are a content creation agent for an AI Second Brain. "
        "You draft content in the user's authentic voice using their accumulated knowledge.\n\n"
        "OUTPUT RULES (CRITICAL):\n"
        "- The 'draft' field MUST contain the COMPLETE written text — the actual post, email, "
        "or article the user will publish. NEVER put a summary or description of what you wrote.\n"
        "- The 'notes' field is for editorial suggestions to the human reviewer.\n"
        "- The 'patterns_applied' and 'voice_elements' fields track what you used.\n"
        "- Set word_count to the actual word count of the draft.\n\n"
        "VOICE (CRITICAL):\n"
        "- Your prompt includes the user's VOICE GUIDE and REFERENCE EXAMPLES — study them carefully.\n"
        "- Mirror the user's actual writing style, sentence rhythm, word choices, and personality.\n"
        "- The voice guide IS the voice. Do not default to generic 'professional' or 'casual' tone.\n"
        "- If no voice guide is provided, write in a clear, direct, conversational tone.\n\n"
        "PROCESS:\n"
        "1. Study the voice guide and reference examples in your prompt.\n"
        "2. Use find_applicable_patterns to find topic-specific writing patterns.\n"
        "3. Follow the Five Writing Laws: active voice, remove needless words, no adverbs, "
        "write simply, hit the reader with the first sentence.\n"
        "4. AVOID AI patterns: no em dashes for drama, no 'Here's the thing:', "
        "no fake enthusiasm ('amazing', 'incredible'), "
        "no generic intros ('In today's fast-paced world...').\n"
        "5. Let the content be as long or short as it needs to be. "
        "Follow the length guidance but don't pad or truncate artificially.\n"
        "6. Call validate_draft to check structure requirements.\n"
        "7. Produce a DRAFT for human editing, not final copy.\n\n"
        "ERROR HANDLING: If brain context tools (voice guide, patterns, examples) "
        "return 'BACKEND_ERROR:' messages, write the best draft you can without that "
        "context. Set the error field to describe which services were unavailable. "
        "A draft without voice matching is better than no draft at all."
    ),
)


@create_agent.instructions
async def inject_content_types(ctx: RunContext[BrainDeps]) -> str:
    """Inject available content types and per-type writing instructions."""
    try:
        registry = ctx.deps.get_content_type_registry()
        types = await registry.get_all()
        if not types:
            return "No custom content types configured. Use default types: linkedin, email, comment."

        type_list = []
        for slug, ct in types.items():
            if ct.length_guidance:
                # Use first sentence of length_guidance for compact display
                length_info = ct.length_guidance.split(".")[0].strip()
            else:
                length_info = f"~{ct.max_words} words" if ct.max_words else "flexible length"
            type_list.append(f"- {slug}: {ct.name} ({length_info})")

        parts = ["Available content types:\n" + "\n".join(type_list)]

        # Inject writing instructions for all types that have them
        instructions_section = []
        for slug, ct in types.items():
            if ct.writing_instructions:
                instructions_section.append(
                    f"\n### {ct.name} ({slug}) — Writing Rules:\n{ct.writing_instructions}"
                )
        if instructions_section:
            parts.append(
                "\n## Per-Type Writing Instructions"
                + "".join(instructions_section)
            )

        return "\n".join(parts)
    except Exception:
        return "Content type registry unavailable. Use default types."


@create_agent.output_validator
async def validate_create(ctx: RunContext[BrainDeps], output: CreateResult) -> CreateResult:
    """Validate draft completeness and quality — accept degraded output on backend errors."""
    # Backend error signaled — accept as-is (draft may be minimal)
    if output.error:
        return output
    # Draft must be substantial
    word_count = len(output.draft.split())
    if word_count < 20:
        raise ModelRetry(
            f"Draft is only {word_count} words. The draft field MUST contain the "
            "COMPLETE written text — the actual post, email, or document. "
            "NOT a summary or description. Write the full content.\n"
            "If brain context tools return errors, set the error field and "
            "write the best draft you can without brain context."
        )

    # Detect summary-instead-of-draft anti-pattern
    summary_indicators = [
        "here is a draft", "here's a draft", "i would write",
        "the draft would", "this draft covers", "i've created a",
    ]
    draft_lower = output.draft.lower()[:200]
    for indicator in summary_indicators:
        if indicator in draft_lower:
            raise ModelRetry(
                f"The draft appears to be a DESCRIPTION of content, not the content itself. "
                f"Detected: '{indicator}'. The draft field must contain the actual "
                "publishable text that the user will copy and paste. Remove any meta-commentary "
                "and write the actual content."
            )

    # Set word_count if not already set
    if output.word_count == 0:
        output.word_count = word_count

    return output


@create_agent.tool
async def load_voice_guide(ctx: RunContext[BrainDeps]) -> str:
    """Load the user's voice and tone guide from the brain for style matching."""
    try:
        return await load_voice_context(ctx.deps, include_graph=True)
    except Exception as e:
        return tool_error("load_voice_guide", e)


@create_agent.tool
async def load_content_examples(
    ctx: RunContext[BrainDeps], content_type: str
) -> str:
    """Load reference examples of a specific content type from the brain.
    Use this to study the user's past work before drafting."""
    try:
        examples = await ctx.deps.storage_service.get_examples(
            content_type=content_type
        )
        if not examples:
            return f"No examples found for type '{content_type}'."
        limit = ctx.deps.config.experience_limit
        sections = []
        for ex in examples[:limit]:
            title = ex.get("title", "Untitled")
            text = ex.get("content", "")[:ctx.deps.config.content_preview_limit]
            sections.append(f"### {title}\n{text}")
        return f"## Examples ({content_type})\n" + "\n\n".join(sections)
    except Exception as e:
        return tool_error("load_content_examples", e)


@create_agent.tool
async def find_applicable_patterns(
    ctx: RunContext[BrainDeps], topic: str, content_type: str = ""
) -> str:
    """Find brain patterns and semantic memories relevant to the content topic.
    When content_type is provided, uses filtered semantic search for that type."""
    try:
        # Semantic search for general memories about the topic
        result = await ctx.deps.memory_service.search(topic)
        general_relations = result.relations
        reranked_general = await rerank_memories(ctx.deps, topic, result.memories)

        # Semantic search for patterns (optionally filtered by content type)
        pattern_memories = []
        pattern_relations = []
        try:
            if content_type:
                filters = {
                    "AND": [
                        {"category": "pattern"},
                        {"applicable_content_types": {"contains": content_type}},
                    ]
                }
            else:
                filters = {"category": "pattern"}
            pattern_result = await ctx.deps.memory_service.search_with_filters(
                topic,
                metadata_filters=filters,
                limit=10,
            )
            pattern_memories = pattern_result.memories
            pattern_relations = pattern_result.relations
        except Exception:
            logger.debug("Semantic pattern search failed in create_agent")

        pattern_memories = await rerank_memories(ctx.deps, topic, pattern_memories)

        # Also check Graphiti for deeper entity relationships
        graphiti_relations = await search_with_graph_fallback(ctx.deps, topic)

        # Fall back to Supabase patterns (structured data)
        patterns = await ctx.deps.storage_service.get_patterns()

        # Filter patterns by content type if provided (Supabase fallback)
        if content_type and patterns:
            type_specific = [
                p for p in patterns
                if p.get("applicable_content_types")
                and content_type in p["applicable_content_types"]
            ]
            universal = [
                p for p in patterns
                if p.get("applicable_content_types") is None
            ]
            patterns = type_specific + universal

        sections = []

        if pattern_memories:
            mem_lines = ["## Semantically Matched Patterns"]
            mem_lines.append(format_memories(pattern_memories))
            sections.append("\n".join(mem_lines))

        if patterns:
            pattern_lines = ["## Pattern Registry"]
            for p in patterns:
                text = p.get("pattern_text", "")[:ctx.deps.config.pattern_preview_limit]
                types_label = ""
                if p.get("applicable_content_types"):
                    types_label = f" [{', '.join(p['applicable_content_types'])}]"
                pattern_lines.append(
                    f"- [{p.get('confidence', 'LOW')}] **{p['name']}**{types_label}: {text}"
                )
            sections.append("\n".join(pattern_lines))

        if reranked_general:
            mem_lines = ["## Semantic Memory"]
            for m in reranked_general[:5]:
                memory = m.get("memory", m.get("result", ""))
                mem_lines.append(f"- {memory}")
            sections.append("\n".join(mem_lines))

        # Merge all graph relations (general + pattern + Graphiti)
        all_relations = (general_relations or []) + pattern_relations + graphiti_relations
        rel_text = format_relations(all_relations)
        if rel_text:
            sections.append(rel_text)

        return "\n\n".join(sections) if sections else "No applicable patterns found."
    except Exception as e:
        return tool_error("find_applicable_patterns", e)


@create_agent.tool
async def load_audience_context(ctx: RunContext[BrainDeps]) -> str:
    """Load audience and customer context from the brain for targeting."""
    try:
        audience = await ctx.deps.storage_service.get_memory_content("audience")
        customers = await ctx.deps.storage_service.get_memory_content("customers")

        sections = []
        for label, items in [("Audience", audience), ("Customers", customers)]:
            if items:
                lines = [f"## {label}"]
                for item in items:
                    title = item.get("title", "Untitled")
                    text = item.get("content", "")[:ctx.deps.config.content_preview_limit]
                    lines.append(f"### {title}\n{text}")
                sections.append("\n".join(lines))

        if not sections:
            return "No audience context found. Write for a general professional audience."
        return "\n\n".join(sections)
    except Exception as e:
        return tool_error("load_audience_context", e)


@create_agent.tool
async def validate_draft(
    ctx: RunContext[BrainDeps],
    draft: str,
    content_type: str,
) -> str:
    """Validate a draft against content type requirements.

    Checks word count, required sections, and type-specific validation rules.
    Call this before finalizing the draft.
    """
    try:
        registry = ctx.deps.get_content_type_registry()
        config = await registry.get(content_type)
        if not config:
            return f"Unknown content type: '{content_type}'. Skipping validation."

        issues = []
        word_count = len(draft.split())

        # Word count from max_words (soft advisory)
        if config.max_words and config.max_words > 0:
            if word_count > config.max_words:
                issues.append(
                    f"Consider tightening — the draft is {word_count} words "
                    f"(typical max for {content_type} is {config.max_words}). "
                    "Only trim if there's actual fluff."
                )
            elif word_count < config.max_words * 0.2:
                issues.append(
                    f"Draft is only {word_count} words — quite short for {content_type}. "
                    "Make sure the content is complete, not just an outline."
                )

        # Min words from validation_rules
        min_words = config.validation_rules.get("min_words", 0)
        if min_words and word_count < min_words:
            issues.append(
                f"Draft is {word_count} words, below the suggested minimum of "
                f"{min_words} for {content_type}. Ensure the content is complete."
            )

        # Required sections from validation_rules
        required = config.validation_rules.get("required_sections", [])
        for section in required:
            if section.lower() not in draft.lower():
                issues.append(f"Missing required section: '{section}'")

        # Structure hints (existing check)
        if config.structure_hint:
            hint_sections = [s.strip() for s in config.structure_hint.split("|") if s.strip()]
            for section in hint_sections:
                if section.lower() not in draft.lower():
                    issues.append(f"Missing expected section: '{section}'")

        # Custom checks from validation_rules
        custom = config.validation_rules.get("custom_checks", [])
        if "title_required" in custom:
            first_line = draft.strip().split("\n")[0].strip()
            if len(first_line) > 200 or first_line.endswith("."):
                issues.append("Content should start with a clear title (first line, no period).")
        if "substantial_content" in custom:
            if word_count < 100:
                issues.append(
                    f"Content is only {word_count} words. This content type requires "
                    "substantial, complete content — not a summary or outline."
                )

        if not issues:
            return f"Draft validates OK. Word count: {word_count}/{config.max_words or 'unlimited'}."
        return "Validation issues:\n" + "\n".join(f"- {i}" for i in issues)
    except Exception as e:
        return tool_error("validate_draft", e)
