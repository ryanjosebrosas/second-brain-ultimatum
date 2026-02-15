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
    return BrainDeps(
        config=config,
        memory_service=MemoryService(config),
        storage_service=StorageService(config),
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
        if output.next_action:
            click.echo(f"\nNext: {output.next_action}")

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
