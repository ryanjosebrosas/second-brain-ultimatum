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
def health():
    """Check brain health and growth metrics."""
    deps = create_deps()

    async def _health():
        patterns = await deps.storage_service.get_patterns()
        experiences = await deps.storage_service.get_experiences()
        total = len(patterns)
        high = len([p for p in patterns if p.get("confidence") == "HIGH"])
        medium = len([p for p in patterns if p.get("confidence") == "MEDIUM"])
        low = len([p for p in patterns if p.get("confidence") == "LOW"])

        # Topic breakdown
        topics: dict[str, int] = {}
        for p in patterns:
            t = p.get("topic", "uncategorized")
            topics[t] = topics.get(t, 0) + 1

        try:
            memory_count = await deps.memory_service.get_memory_count()
        except Exception:
            memory_count = "unavailable"

        latest = patterns[0].get("date_updated", "unknown") if patterns else "none"
        graph = deps.config.graph_provider or "disabled"

        click.echo(f"Memories: {memory_count}")
        click.echo(f"Patterns: {total} (HIGH: {high}, MEDIUM: {medium}, LOW: {low})")
        click.echo(f"Experiences: {len(experiences)}")
        click.echo(f"Graph: {graph}")
        click.echo(f"Last updated: {latest}")
        if topics:
            click.echo("\nPatterns by Topic:")
            for t, c in sorted(topics.items()):
                click.echo(f"  {t}: {c}")
        click.echo(f"\nStatus: {'GROWING' if total > 5 else 'BUILDING'}")

    asyncio.run(_health())


@cli.command()
def migrate():
    """Migrate markdown data to Mem0 + Supabase."""
    from second_brain.migrate import run_migration

    click.echo("Starting migration...")
    asyncio.run(run_migration())
    click.echo("Migration complete!")


if __name__ == "__main__":
    cli()
