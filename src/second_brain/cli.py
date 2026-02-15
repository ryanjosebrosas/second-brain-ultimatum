"""CLI entry points for the AI Second Brain."""

import asyncio
import logging
import sys

import click

# Fix Windows terminal encoding for Unicode (emoji etc.)
if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from second_brain.config import BrainConfig
from second_brain.deps import BrainDeps
from second_brain.models import get_model
from second_brain.services.memory import MemoryService
from second_brain.services.storage import StorageService

logger = logging.getLogger(__name__)


def create_deps() -> BrainDeps:
    """Create the dependency container with all services."""
    config = BrainConfig()
    graphiti = None
    if config.graph_provider == "graphiti":
        try:
            from second_brain.services.graphiti import GraphitiService
            graphiti = GraphitiService(config)
        except ImportError:
            logger.warning("graphiti-core not installed. Install with: "
                           "pip install -e '.[graphiti]'")

    return BrainDeps(
        config=config,
        memory_service=MemoryService(config),
        storage_service=StorageService(config),
        graphiti_service=graphiti,
    )


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
def cli(verbose: bool):
    """AI Second Brain — Your intelligent business companion."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


@cli.command()
@click.argument("query")
def recall(query: str):
    """Search your brain's memory for relevant context."""
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
        metrics = await HealthService().compute_growth(deps, days=days)

        click.echo(f"\n# Growth Report ({days} days)\n")
        click.echo(f"Status: {metrics.status}")
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

    asyncio.run(_growth())


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


@cli.command()
def migrate():
    """Migrate markdown data to Mem0 + Supabase."""
    from second_brain.migrate import run_migration

    click.echo("Starting migration...")
    asyncio.run(run_migration())
    click.echo("Migration complete!")


if __name__ == "__main__":
    cli()
