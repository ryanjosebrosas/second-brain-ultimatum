"""CLI entry points for the AI Second Brain."""

import asyncio
import logging
import sys

import click

# Fix Windows terminal encoding for Unicode (emoji etc.)
if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from second_brain.deps import BrainDeps, create_deps
from second_brain.models import get_model

logger = logging.getLogger(__name__)


def _validate_input(text: str, max_length: int = 10000, label: str = "input") -> str:
    """Validate and sanitize CLI text input."""
    text = text.strip()
    if not text:
        raise click.BadParameter(f"{label} cannot be empty")
    if len(text) > max_length:
        raise click.BadParameter(
            f"{label} too long ({len(text)} chars, max {max_length})"
        )
    return text


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--subscription", "-s", is_flag=True, help="Use Claude subscription auth (overrides config)")
def cli(verbose: bool, subscription: bool):
    """AI Second Brain — Your intelligent business companion."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")
    if subscription:
        import os
        os.environ["USE_SUBSCRIPTION"] = "true"


@cli.command()
@click.argument("query")
def recall(query: str):
    """Search your brain's memory for relevant context."""
    query = _validate_input(query, label="query")
    from second_brain.agents.recall import recall_agent

    deps = create_deps()
    model = get_model(deps.config)

    async def run():
        result = await recall_agent.run(
            f"Search memory for: {query}",
            deps=deps,
            model=model,
        )
        output = result.output

        click.echo(f"\n# Recall: {output.query}\n")
        if output.matches:
            click.echo("## Matches\n")
            for m in output.matches:
                click.echo(f"  [{m.relevance}] {m.content}")
                if m.source:
                    click.echo(f"         Source: {m.source}")
        if output.patterns:
            click.echo("\n## Related Patterns\n")
            for p in output.patterns:
                click.echo(f"  - {p}")
        if output.relations:
            click.echo("\n## Graph Relationships\n")
            for rel in output.relations:
                click.echo(f"  {rel.source} --[{rel.relationship}]--> {rel.target}")
        if output.summary:
            click.echo(f"\n## Summary\n{output.summary}")

    asyncio.run(run())


@cli.command()
@click.argument("question")
def ask(question: str):
    """Get instant help powered by your brain's knowledge."""
    question = _validate_input(question, label="question")
    from second_brain.agents.ask import ask_agent

    deps = create_deps()
    model = get_model(deps.config)

    async def run():
        result = await ask_agent.run(
            question,
            deps=deps,
            model=model,
        )
        output = result.output

        click.echo(f"\n{output.answer}\n")
        if output.context_used:
            click.echo("---")
            click.echo(f"Context: {', '.join(output.context_used)}")
        if output.patterns_applied:
            click.echo(f"Patterns: {', '.join(output.patterns_applied)}")
        if output.relations:
            click.echo("\n## Graph Relationships\n")
            for rel in output.relations:
                click.echo(f"  {rel.source} --[{rel.relationship}]--> {rel.target}")
        if output.next_action:
            click.echo(f"\nNext: {output.next_action}")

    asyncio.run(run())


@cli.command()
@click.argument("content")
@click.option(
    "--category",
    default="general",
    help="Experience category (content, prospects, clients, general)",
)
def learn(content: str, category: str):
    """Extract patterns and learnings from a work session or experience."""
    content = _validate_input(content, label="content")
    from second_brain.agents.learn import learn_agent

    deps = create_deps()
    model = get_model(deps.config)

    async def run():
        result = await learn_agent.run(
            f"Extract learnings from this work session (category: {category}):\n\n{content}",
            deps=deps,
            model=model,
        )
        output = result.output

        click.echo(f"\n# Learn: {output.input_summary}\n")

        if output.patterns_extracted:
            click.echo("## Patterns Extracted\n")
            for p in output.patterns_extracted:
                marker = "(reinforced)" if p.is_reinforcement else "(new)"
                click.echo(f"  [{p.confidence}] {p.name} {marker}")
                click.echo(f"         {p.pattern_text[:100]}")
                if p.anti_patterns:
                    click.echo(f"         Anti: {', '.join(p.anti_patterns[:2])}")

        if output.insights:
            click.echo("\n## Insights\n")
            for insight in output.insights:
                click.echo(f"  - {insight}")

        if output.experience_recorded:
            click.echo(f"\n## Experience: recorded ({output.experience_category})")

        click.echo(f"\n## Summary")
        click.echo(f"  New patterns: {output.patterns_new}")
        click.echo(f"  Reinforced: {output.patterns_reinforced}")
        click.echo(f"  {output.storage_summary}")

    asyncio.run(run())


@cli.command()
@click.argument("prompt")
@click.option(
    "--type",
    "content_type",
    default="linkedin",
    help="Content type slug (run 'brain types list' to see available types)",
)
@click.option(
    "--mode",
    "mode",
    default=None,
    help="Communication mode (casual, professional, formal). Defaults to type's default.",
)
def create(prompt: str, content_type: str, mode: str | None):
    """Draft content in your voice using brain knowledge."""
    prompt = _validate_input(prompt, label="prompt")
    from second_brain.agents.create import create_agent

    deps = create_deps()
    model = get_model(deps.config)
    registry = deps.get_content_type_registry()

    async def run():
        type_config = await registry.get(content_type)
        if not type_config:
            available = await registry.slugs()
            click.echo(f"Unknown content type '{content_type}'. Available: {', '.join(available)}")
            return

        effective_mode = mode or type_config.default_mode

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

        click.echo(f"\n# Draft ({output.content_type} - {output.mode})\n")
        click.echo(output.draft)
        click.echo(f"\n---")
        click.echo(f"Words: {output.word_count}")

        if output.voice_elements:
            click.echo(f"\nVoice: {', '.join(output.voice_elements)}")
        if output.patterns_applied:
            click.echo(f"Patterns: {', '.join(output.patterns_applied)}")
        if output.examples_referenced:
            click.echo(f"Examples: {', '.join(output.examples_referenced)}")
        if output.notes:
            click.echo(f"\nEditor notes: {output.notes}")

    asyncio.run(run())


@cli.command()
@click.argument("content")
@click.option("--type", "content_type", default=None, help="Content type for context (linkedin, email, etc.)")
def review(content: str, content_type: str | None):
    """Review content quality across 6 dimensions with a structured scorecard."""
    content = _validate_input(content, label="content")
    from second_brain.agents.review import run_full_review

    deps = create_deps()
    model = get_model(deps.config)

    async def run():
        result = await run_full_review(content, deps, model, content_type)

        click.echo(f"\n# Review: {result.overall_score}/10 — {result.verdict}\n")

        if result.summary:
            click.echo(f"{result.summary}\n")

        click.echo("## Scores by Dimension\n")
        for s in result.scores:
            click.echo(f"  {s.dimension:20s} {s.score}/10  [{s.status}]")

        if result.top_strengths:
            click.echo("\n## Strengths\n")
            for strength in result.top_strengths:
                click.echo(f"  - {strength}")

        if result.critical_issues:
            click.echo("\n## Issues (Must Fix)\n")
            for issue in result.critical_issues:
                click.echo(f"  - {issue}")

        if result.next_steps:
            click.echo("\n## Next Steps\n")
            for step in result.next_steps:
                click.echo(f"  - {step}")

    asyncio.run(run())


@cli.command()
@click.option("--type", "content_type", default=None, help="Filter by content type (linkedin, email, etc.)")
def examples(content_type: str | None):
    """Search content examples in your brain."""
    deps = create_deps()

    async def _search():
        results = await deps.storage_service.get_examples(content_type=content_type)
        if not results:
            click.echo("No content examples found.")
            return
        for e in results:
            click.echo(f"\n[{e['content_type']}] {e['title']}")
            preview = e.get("content", "")[:300]
            if preview:
                click.echo(f"  {preview}")

    asyncio.run(_search())


@cli.command()
@click.option("--category", default=None, help="Filter by category (framework, methodology, etc.)")
def knowledge(category: str | None):
    """Search the knowledge repository."""
    deps = create_deps()

    async def _search():
        results = await deps.storage_service.get_knowledge(category=category)
        if not results:
            click.echo("No knowledge entries found.")
            return
        for k in results:
            click.echo(f"\n[{k['category']}] {k['title']}")
            preview = k.get("content", "")[:300]
            if preview:
                click.echo(f"  {preview}")

    asyncio.run(_search())


@cli.command()
@click.argument("table", type=click.Choice(["pattern", "experience", "example", "knowledge"]))
@click.argument("item_id")
def delete(table: str, item_id: str):
    """Delete an item from the brain by table and ID."""
    item_id = _validate_input(item_id, max_length=100, label="item_id")
    deps = create_deps()

    async def _delete():
        method = {
            "pattern": deps.storage_service.delete_pattern,
            "experience": deps.storage_service.delete_experience,
            "example": deps.storage_service.delete_example,
            "knowledge": deps.storage_service.delete_knowledge,
        }[table]
        deleted = await method(item_id)
        if deleted:
            click.echo(f"Deleted {table} {item_id}")
        else:
            click.echo(f"No {table} found with ID {item_id}")

    asyncio.run(_delete())


@cli.command()
def health():
    """Check brain health and growth metrics."""
    from second_brain.services.health import HealthService

    deps = create_deps()

    async def _health():
        metrics = await HealthService().compute(deps)
        click.echo(f"Memories: {metrics.memory_count}")
        click.echo(f"Patterns: {metrics.total_patterns} (HIGH: {metrics.high_confidence}, MEDIUM: {metrics.medium_confidence}, LOW: {metrics.low_confidence})")
        click.echo(f"Experiences: {metrics.experience_count}")
        click.echo(f"Graph: {metrics.graph_provider}")
        if metrics.graphiti_status != "disabled":
            click.echo(f"Graphiti: {metrics.graphiti_status} (backend: {metrics.graphiti_backend})")
        click.echo(f"Last updated: {metrics.latest_update}")
        if metrics.topics:
            click.echo("\nPatterns by Topic:")
            for t, c in sorted(metrics.topics.items()):
                click.echo(f"  {t}: {c}")
        click.echo(f"\nStatus: {metrics.status}")

    asyncio.run(_health())


@cli.command()
@click.option("--days", default=30, help="Number of days for the report")
def growth(days: int):
    """View growth report with pattern activity and quality trends."""
    from second_brain.services.health import HealthService

    deps = create_deps()

    async def _growth():
        health = HealthService()
        metrics = await health.compute_growth(deps, days=days)

        click.echo(f"\n# Growth Report ({days} days)\n")
        click.echo(f"Status: {metrics.status}")
        if metrics.graphiti_status != "disabled":
            click.echo(f"Graphiti: {metrics.graphiti_status} (backend: {metrics.graphiti_backend})")
        click.echo(f"Patterns: {metrics.total_patterns} (HIGH: {metrics.high_confidence}, "
                   f"MEDIUM: {metrics.medium_confidence}, LOW: {metrics.low_confidence})")
        click.echo(f"\nGrowth Activity:")
        click.echo(f"  Events total: {metrics.growth_events_total}")
        click.echo(f"  Patterns created: {metrics.patterns_created_period}")
        click.echo(f"  Patterns reinforced: {metrics.patterns_reinforced_period}")
        click.echo(f"  Confidence upgrades: {metrics.confidence_upgrades_period}")

        if metrics.reviews_completed_period > 0:
            click.echo(f"\nQuality Metrics:")
            click.echo(f"  Reviews: {metrics.reviews_completed_period}")
            click.echo(f"  Avg score: {metrics.avg_review_score}/10")
            click.echo(f"  Trend: {metrics.review_score_trend}")

        if metrics.stale_patterns:
            click.echo(f"\nStale Patterns (no activity in 30+ days):")
            for name in metrics.stale_patterns:
                click.echo(f"  - {name}")

        if metrics.topics:
            click.echo(f"\nPatterns by Topic:")
            for t, c in sorted(metrics.topics.items()):
                click.echo(f"  {t}: {c}")

        # Milestones
        try:
            milestone_data = await health.compute_milestones(deps)
            click.echo(f"\n--- Brain Level: {milestone_data['level']} ---")
            click.echo(f"  {milestone_data['level_description']}")
            click.echo(f"  Milestones: {milestone_data['milestones_completed']}/{milestone_data['milestones_total']}")
            if milestone_data.get("next_milestone"):
                click.echo(f"  Next: {milestone_data['next_milestone']}")
            click.echo()
            for m in milestone_data.get("milestones", []):
                icon = "[x]" if m["completed"] else "[ ]"
                click.echo(f"  {icon} {m['description']}")
        except Exception:
            logger.debug("Milestone computation failed (non-critical)")

        # Quality trending
        try:
            quality = await health.compute_quality_trend(deps, days=days)
            if quality.get("total_reviews", 0) > 0:
                click.echo(f"\n--- Quality Trending ({days} days) ---")
                click.echo(f"  Reviews: {quality['total_reviews']}")
                click.echo(f"  Avg Score: {quality['avg_score']}")
                click.echo(f"  Trend: {quality['score_trend']}")
                if quality.get("excellence_count"):
                    click.echo(f"  Excellence (9+): {quality['excellence_count']}")
                if quality.get("needs_work_count"):
                    click.echo(f"  Needs Work (<6): {quality['needs_work_count']}")
                if quality.get("by_content_type"):
                    click.echo("  By Type:")
                    for ct, score in quality["by_content_type"].items():
                        click.echo(f"    {ct}: {score}")
                if quality.get("recurring_issues"):
                    click.echo("  Recurring Issues:")
                    for issue in quality["recurring_issues"][:5]:
                        click.echo(f"    - {issue}")
        except Exception:
            logger.debug("Quality trending failed (non-critical)")

    asyncio.run(_growth())


@cli.command()
@click.option("--min-cluster", default=3, type=int,
               help="Minimum memories to form a pattern cluster")
def consolidate(min_cluster: int):
    """Consolidate accumulated memories into patterns."""
    from second_brain.agents.learn import learn_agent

    deps = create_deps()
    model = get_model(deps.config)

    async def run():
        result = await learn_agent.run(
            f"Run memory consolidation with min_cluster_size={min_cluster}. "
            f"Use the consolidate_memories tool to review accumulated memories, "
            f"then use store_pattern and reinforce_existing_pattern to act on findings. "
            f"Tag graduated memories with tag_graduated_memories when done.",
            deps=deps,
            model=model,
        )
        output = result.output

        click.echo(f"\n# Brain Consolidation\n")
        click.echo(f"Summary: {output.input_summary}\n")

        if output.patterns_extracted:
            click.echo("## Patterns Identified\n")
            for p in output.patterns_extracted:
                marker = "(reinforced)" if p.is_reinforcement else "(new)"
                click.echo(f"  [{p.confidence}] {p.name} {marker}")

        click.echo(f"\nResults: {output.patterns_new} new, "
                   f"{output.patterns_reinforced} reinforced")

    asyncio.run(run())


@cli.group()
def types():
    """Manage content types in your brain."""
    pass


@types.command("list")
def types_list():
    """List all available content types."""
    deps = create_deps()
    registry = deps.get_content_type_registry()

    async def _list():
        all_types = await registry.get_all()
        if not all_types:
            click.echo("No content types found.")
            return
        click.echo(f"\n{'Slug':<20} {'Name':<25} {'Mode':<15} {'Words':<8} {'Built-in'}")
        click.echo("-" * 80)
        for slug, config in sorted(all_types.items()):
            builtin = "yes" if config.is_builtin else "no"
            click.echo(f"{slug:<20} {config.name:<25} {config.default_mode:<15} {config.max_words:<8} {builtin}")
            if config.review_dimensions:
                enabled = [d.name for d in config.review_dimensions if d.enabled]
                click.echo(f"  Review dims: {', '.join(enabled)}")

    asyncio.run(_list())


@types.command("add")
@click.argument("slug")
@click.argument("name")
@click.option("--mode", default="professional", help="Default mode: casual, professional, formal")
@click.option("--structure", required=True, help="Structure hint (e.g., 'Hook -> Body -> CTA')")
@click.option("--max-words", default=500, type=int, help="Target word count")
@click.option("--description", default="", help="Type description")
def types_add(slug: str, name: str, mode: str, structure: str, max_words: int, description: str):
    """Add a new content type. SLUG should be lowercase kebab-case (e.g., newsletter, blog-post)."""
    deps = create_deps()

    async def _add():
        row = {
            "slug": slug,
            "name": name,
            "default_mode": mode,
            "structure_hint": structure,
            "example_type": slug,
            "max_words": max_words,
            "description": description,
            "is_builtin": False,
        }
        result = await deps.storage_service.upsert_content_type(row)
        if result:
            click.echo(f"Added content type '{slug}' ({name})")
        else:
            click.echo(f"Failed to add content type '{slug}'")

    asyncio.run(_add())


@types.command("remove")
@click.argument("slug")
@click.option("--force", is_flag=True, help="Skip confirmation for built-in types")
def types_remove(slug: str, force: bool):
    """Remove a content type by slug."""
    deps = create_deps()

    async def _remove():
        existing = await deps.storage_service.get_content_type_by_slug(slug)
        if not existing:
            click.echo(f"No content type found with slug '{slug}'")
            return
        if existing.get("is_builtin") and not force:
            click.echo(f"'{slug}' is a built-in type. Use --force to remove it.")
            return
        deleted = await deps.storage_service.delete_content_type(slug)
        if deleted:
            click.echo(f"Removed content type '{slug}'")
        else:
            click.echo(f"Failed to remove '{slug}'")

    asyncio.run(_remove())


@cli.group()
def graph():
    """Manage Graphiti knowledge graph."""
    pass


@graph.command("health")
def graph_health():
    """Check Graphiti graph backend health and connectivity."""
    deps = create_deps()

    async def _health():
        if not deps.graphiti_service:
            click.echo("Graphiti is not enabled. Set GRAPHITI_ENABLED=true in .env")
            return
        health = await deps.graphiti_service.health_check()
        click.echo(f"Status: {health.get('status', 'unknown')}")
        click.echo(f"Backend: {health.get('backend', 'none')}")
        if health.get("error"):
            click.echo(f"Error: {health['error']}")

    asyncio.run(_health())


@graph.command("search")
@click.argument("query")
@click.option("--limit", default=10, type=int, help="Max results")
def graph_search(query: str, limit: int):
    """Search Graphiti knowledge graph for entity relationships."""
    deps = create_deps()

    async def _search():
        if not deps.graphiti_service:
            click.echo("Graphiti is not enabled. Set GRAPHITI_ENABLED=true in .env")
            return
        results = await deps.graphiti_service.search(query, limit=limit)
        if not results:
            click.echo("No graph relationships found.")
            return
        click.echo(f"\n# Graph Search: {query}\n")
        for rel in results:
            src = rel.get("source", "?")
            relationship = rel.get("relationship", "?")
            tgt = rel.get("target", "?")
            click.echo(f"  {src} --[{relationship}]--> {tgt}")
        click.echo(f"\nFound {len(results)} relationship(s)")

    asyncio.run(_search())


# --- Project Lifecycle ---

@cli.group()
def project():
    """Manage project lifecycle (plan -> execute -> review -> learn)."""
    pass


@project.command("create")
@click.argument("name")
@click.option("--category", type=click.Choice(["content", "prospects", "clients", "products", "general"]),
              default="content", help="Project category")
@click.option("--description", default=None, help="Project description")
def project_create(name: str, category: str, description: str | None):
    """Create a new project and start planning phase."""
    name = _validate_input(name, label="name")
    deps = create_deps()

    async def run():
        project_data = {
            "name": name,
            "category": category,
            "lifecycle_stage": "planning",
        }
        if description:
            project_data["description"] = description
        result = await deps.storage_service.create_project(project_data)
        if result:
            click.echo(f"\nProject created: {result.get('name', name)}")
            click.echo(f"  ID: {result.get('id', 'unknown')}")
            click.echo(f"  Stage: planning")
            click.echo(f"  Category: {category}")
            click.echo(f"\nNext: Add a plan artifact or advance to 'executing'")
        else:
            click.echo("Failed to create project.", err=True)

    asyncio.run(run())


@project.command("status")
@click.argument("project_id")
def project_status(project_id: str):
    """Show project status and artifacts."""
    project_id = _validate_input(project_id, label="project_id")
    deps = create_deps()

    async def run():
        proj = await deps.storage_service.get_project(project_id)
        if not proj:
            click.echo(f"Project not found: {project_id}", err=True)
            return

        stage_icons = {
            "planning": "[plan]", "executing": "[exec]", "reviewing": "[review]",
            "learning": "[learn]", "complete": "[done]", "archived": "[arch]",
        }
        icon = stage_icons.get(proj.get("lifecycle_stage", ""), "[?]")
        click.echo(f"\n{icon} {proj['name']}")
        click.echo(f"  Stage: {proj.get('lifecycle_stage', 'unknown')}")
        click.echo(f"  Category: {proj.get('category', 'unknown')}")
        if proj.get("review_score"):
            click.echo(f"  Review Score: {proj['review_score']}/10")

        artifacts = proj.get("project_artifacts", [])
        if artifacts:
            click.echo(f"\n  Artifacts ({len(artifacts)}):")
            for a in artifacts:
                click.echo(f"    - {a['artifact_type']}: {a.get('title', 'untitled')}")
        else:
            click.echo("\n  No artifacts yet")

        next_actions = {
            "planning": "Create a plan artifact, then advance to 'executing'",
            "executing": "Work on the project, then advance to 'reviewing'",
            "reviewing": "Run review, then advance to 'learning'",
            "learning": "Run /learn, then advance to 'complete'",
            "complete": "Project complete! Patterns extracted and experiences recorded.",
        }
        stage = proj.get("lifecycle_stage", "")
        if stage in next_actions:
            click.echo(f"\n  Next: {next_actions[stage]}")

    asyncio.run(run())


@project.command("list")
@click.option("--stage", type=click.Choice(["planning", "executing", "reviewing",
              "learning", "complete", "archived"]), default=None)
@click.option("--category", default=None)
def project_list(stage: str | None, category: str | None):
    """List projects with optional filtering."""
    deps = create_deps()

    async def run():
        projects = await deps.storage_service.list_projects(
            lifecycle_stage=stage, category=category
        )
        if not projects:
            click.echo("No projects found.")
            return

        click.echo(f"\n--- Projects ({len(projects)}) ---")
        for p in projects:
            icon = {"planning": "[plan]", "executing": "[exec]", "reviewing": "[review]",
                    "learning": "[learn]", "complete": "[done]", "archived": "[arch]"
            }.get(p.get("lifecycle_stage", ""), "[?]")
            score = f" (score: {p['review_score']})" if p.get("review_score") else ""
            click.echo(f"  {icon} {p['name']} [{p.get('lifecycle_stage')}]{score}")
            click.echo(f"     ID: {p['id']}")

    asyncio.run(run())


@project.command("advance")
@click.argument("project_id")
@click.option("--stage", default=None, help="Target stage (auto-advances if not specified)")
def project_advance(project_id: str, stage: str | None):
    """Advance project to next lifecycle stage."""
    project_id = _validate_input(project_id, label="project_id")
    deps = create_deps()
    stage_order = ["planning", "executing", "reviewing", "learning", "complete"]

    async def run():
        proj = await deps.storage_service.get_project(project_id)
        if not proj:
            click.echo(f"Project not found: {project_id}", err=True)
            return

        current = proj.get("lifecycle_stage", "planning")
        if stage:
            next_stage = stage
        else:
            try:
                idx = stage_order.index(current)
                next_stage = stage_order[idx + 1] if idx + 1 < len(stage_order) else current
            except ValueError:
                click.echo(f"Cannot auto-advance from stage: {current}", err=True)
                return

        result = await deps.storage_service.update_project_stage(project_id, next_stage)
        if result:
            click.echo(f"Project '{proj['name']}' advanced: {current} -> {next_stage}")
        else:
            click.echo("Failed to advance project.", err=True)

    asyncio.run(run())


@cli.command()
def setup():
    """Check brain setup status and get onboarding guidance."""
    deps = create_deps()

    async def run():
        from second_brain.services.health import HealthService
        health = HealthService()
        status = await health.compute_setup_status(deps)

        completed = status.get("completed_count", 0)
        total = status.get("total_steps", 0)
        pct = int(completed / total * 100) if total > 0 else 0

        click.echo(f"\n--- Brain Setup ({pct}% complete) ---")
        click.echo(f"  {completed}/{total} steps done\n")

        for step in status.get("steps", []):
            icon = "[x]" if step["completed"] else "[ ]"
            click.echo(f"  {icon} {step['description']}")

        if status.get("is_complete"):
            click.echo("\n  Your brain is fully configured!")
        else:
            missing = status.get("missing_categories", [])
            if missing:
                click.echo(f"\n  Missing memory categories: {', '.join(missing)}")
                click.echo("  Use 'brain learn' or migration to populate them.")
            click.echo("\n  Run 'brain migrate' to import from your template system.")

    asyncio.run(run())


@cli.command()
def patterns():
    """View the pattern registry -- all patterns with confidence and status."""
    deps = create_deps()

    async def run():
        from second_brain.agents.utils import format_pattern_registry
        registry = await deps.storage_service.get_pattern_registry()
        click.echo(f"\n--- Pattern Registry ---\n")
        click.echo(format_pattern_registry(registry, config=deps.config))

    asyncio.run(run())


@cli.command()
@click.argument("request")
@click.option("--execute/--no-execute", default=False, help="Execute routed agent (not just route)")
def route(request: str, execute: bool):
    """Route a request through the Chief of Staff orchestrator."""
    request = _validate_input(request, label="request")
    from second_brain.agents.chief_of_staff import chief_of_staff

    deps = create_deps()
    model = get_model(deps.config)

    async def run():
        # Step 1: Get routing decision
        result = await chief_of_staff.run(request, deps=deps, model=model)
        routing = result.output

        click.echo(f"\nRoute: {routing.target_agent}")
        click.echo(f"Reasoning: {routing.reasoning}")
        if routing.pipeline_steps:
            click.echo(f"Pipeline: {' -> '.join(routing.pipeline_steps)}")
        click.echo(f"Confidence: {routing.confidence}")

        if not execute:
            click.echo("\nUse --execute to run the routed agent.")
            return

        # Step 2: Execute
        if routing.target_agent == "pipeline" and routing.pipeline_steps:
            from second_brain.agents.utils import run_pipeline
            results = await run_pipeline(
                steps=routing.pipeline_steps,
                initial_prompt=request,
                deps=deps,
                model=model,
            )
            final = results.get("final")
            if final:
                click.echo(f"\nPipeline result:\n{final}")
        else:
            from second_brain.agents.utils import get_agent_registry
            registry = get_agent_registry()
            if routing.target_agent in registry:
                agent, desc = registry[routing.target_agent]
                agent_result = await agent.run(request, deps=deps, model=model)
                click.echo(f"\nResult:\n{agent_result.output}")
            else:
                click.echo(f"\nAgent '{routing.target_agent}' not available yet.")

    asyncio.run(run())


@cli.command()
@click.argument("topic")
@click.option("--framework", default=None, help="Essay framework: argumentative/explanatory/narrative")
def essay(topic: str, framework: str | None):
    """Write a long-form essay on a topic."""
    topic = _validate_input(topic, label="topic")
    from second_brain.agents.essay_writer import essay_writer_agent

    deps = create_deps()
    model = get_model(deps.config)
    prompt = f"Write an essay about: {topic}"
    if framework:
        prompt += f"\nUse {framework} framework."

    async def run():
        result = await essay_writer_agent.run(prompt, deps=deps, model=model)
        click.echo(f"\n# {result.output.title}\n")
        click.echo(result.output.essay)
        if result.output.notes:
            click.echo(f"\n---\nNotes: {result.output.notes}")

    asyncio.run(run())


@cli.command()
@click.argument("content")
def clarity(content: str):
    """Analyze content for clarity and readability."""
    content = _validate_input(content, label="content")
    from second_brain.agents.clarity import clarity_agent

    deps = create_deps()
    model = get_model(deps.config)

    async def run():
        result = await clarity_agent.run(content, deps=deps, model=model)
        click.echo(f"\nReadability: {result.output.overall_readability}")
        click.echo(f"Critical issues: {result.output.critical_count}")
        for f in result.output.findings:
            click.echo(f"  [{f.severity}] {f.location}: {f.issue}")
            click.echo(f"    -> {f.suggestion}")

    asyncio.run(run())


@cli.command()
@click.argument("findings")
def synthesize(findings: str):
    """Synthesize review findings into actionable themes."""
    findings = _validate_input(findings, label="findings")
    from second_brain.agents.synthesizer import synthesizer_agent

    deps = create_deps()
    model = get_model(deps.config)

    async def run():
        result = await synthesizer_agent.run(findings, deps=deps, model=model)
        click.echo(f"\n{result.output.total_themes_output} themes, {result.output.implementation_hours:.1f}h total")
        for t in result.output.themes:
            click.echo(f"\n  [{t.priority}] {t.title} ({t.effort_minutes}min)")
            click.echo(f"    Action: {t.action}")

    asyncio.run(run())


@cli.command("templates")
@click.argument("deliverable")
def find_templates(deliverable: str):
    """Analyze a deliverable for template opportunities."""
    deliverable = _validate_input(deliverable, label="deliverable")
    from second_brain.agents.template_builder import template_builder_agent

    deps = create_deps()
    model = get_model(deps.config)

    async def run():
        result = await template_builder_agent.run(deliverable, deps=deps, model=model)
        click.echo(f"\n{result.output.templates_created} template opportunities found")
        for opp in result.output.opportunities:
            click.echo(f"\n  {opp.name}")
            click.echo(f"    When: {opp.when_to_use}")
            click.echo(f"    Saves: {opp.estimated_time_savings}")

    asyncio.run(run())


@cli.command()
@click.argument("request")
@click.option("--session-type", default="morning", help="morning/evening/check_in/intervention")
def coach(request: str, session_type: str):
    """Get daily accountability coaching."""
    request = _validate_input(request, label="request")
    from second_brain.agents.coach import coach_agent

    deps = create_deps()
    model = get_model(deps.config)
    prompt = f"Session type: {session_type}\n\n{request}"

    async def run():
        result = await coach_agent.run(prompt, deps=deps, model=model)
        out = result.output
        click.echo(f"\nSession: {out.session_type}")
        if out.priorities:
            click.echo("Priorities:")
            for p in out.priorities:
                click.echo(f"  - {p}")
        click.echo(f"\nNext action: {out.next_action}")
        if out.coaching_notes:
            click.echo(f"\n{out.coaching_notes}")

    asyncio.run(run())


@cli.command()
@click.argument("tasks")
def prioritize(tasks: str):
    """Get PMO priority scoring for tasks."""
    tasks = _validate_input(tasks, label="tasks")
    from second_brain.agents.pmo import pmo_agent

    deps = create_deps()
    model = get_model(deps.config)

    async def run():
        result = await pmo_agent.run(tasks, deps=deps, model=model)
        out = result.output
        click.echo(f"\n{out.coaching_message}")
        if out.today_focus:
            click.echo(f"\nToday: {', '.join(out.today_focus)}")
        if out.this_week:
            click.echo(f"This week: {', '.join(out.this_week)}")

    asyncio.run(run())


@cli.command("impact")
@click.argument("recommendation")
def analyze_impact(recommendation: str):
    """Quantify business impact of a recommendation."""
    recommendation = _validate_input(recommendation, label="recommendation")
    from second_brain.agents.impact import impact_agent

    deps = create_deps()
    model = get_model(deps.config)

    async def run():
        result = await impact_agent.run(recommendation, deps=deps, model=model)
        click.echo(f"\n{result.output.executive_summary}")
        if result.output.total_roi:
            click.echo(f"\nROI: {result.output.total_roi}")

    asyncio.run(run())


@cli.command()
@click.argument("request")
def email(request: str):
    """Compose or manage emails."""
    request = _validate_input(request, label="request")
    from second_brain.agents.email_agent import email_agent

    deps = create_deps()
    model = get_model(deps.config)

    async def run():
        result = await email_agent.run(request, deps=deps, model=model)
        out = result.output
        if out.subject:
            click.echo(f"\nSubject: {out.subject}")
        click.echo(f"\n{out.body}")
        click.echo(f"\nStatus: {out.status}")

    asyncio.run(run())


@cli.command()
@click.argument("question")
def analyze(question: str):
    """Get data analysis and business insights."""
    question = _validate_input(question, label="question")
    from second_brain.agents.analyst import analyst_agent

    deps = create_deps()
    model = get_model(deps.config)

    async def run():
        result = await analyst_agent.run(question, deps=deps, model=model)
        click.echo(f"\n{result.output.executive_summary}")

    asyncio.run(run())


@cli.command("specialist")
@click.argument("question")
def ask_specialist(question: str):
    """Ask a Claude Code specialist question."""
    question = _validate_input(question, label="question")
    from second_brain.agents.specialist import specialist_agent

    deps = create_deps()
    model = get_model(deps.config)

    async def run():
        result = await specialist_agent.run(question, deps=deps, model=model)
        out = result.output
        click.echo(f"\n[{out.confidence_level}] {out.answer}")
        if out.sources:
            click.echo(f"\nSources: {', '.join(out.sources)}")

    asyncio.run(run())


@cli.command()
def migrate():
    """Migrate markdown data to Mem0 + Supabase."""
    from second_brain.migrate import run_migration

    click.echo("Starting migration...")
    asyncio.run(run_migration())
    click.echo("Migration complete!")


if __name__ == "__main__":
    cli()
