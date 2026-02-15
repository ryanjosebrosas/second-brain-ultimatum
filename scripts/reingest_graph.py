"""Re-ingest all Second Brain data with graph memory enabled."""
import asyncio
import logging
import sys

if sys.platform == "win32" and sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from second_brain.config import BrainConfig
from second_brain.services.memory import MemoryService
from second_brain.migrate import BrainMigrator

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


async def reingest():
    config = BrainConfig()
    memory = MemoryService(config)

    # Step 1: Get existing memories
    logger.info("Fetching existing memories...")
    existing = await memory.get_all()
    logger.info(f"Found {len(existing)} existing memories")

    # Step 2: Delete existing Mem0 memories
    logger.info("Deleting existing memories for clean re-import...")
    for mem in existing:
        mem_id = mem.get("id")
        if mem_id:
            await memory.delete(mem_id)
    logger.info(f"Deleted {len(existing)} memories")

    # Step 3: Re-run migration (graph enabled via GRAPH_PROVIDER in .env)
    logger.info("Re-importing data...")
    migrator = BrainMigrator(config)
    await migrator.migrate_memory_content()
    await migrator.migrate_patterns()
    await migrator.migrate_experiences()

    # Step 4: If Graphiti provider, also ingest episodes
    if config.graph_provider == "graphiti":
        try:
            from second_brain.services.graphiti import GraphitiService

            logger.info("Ingesting episodes into Graphiti...")
            graphiti = GraphitiService(config)
            for category_dir in (config.brain_data_path / "memory").iterdir():
                if not category_dir.is_dir():
                    continue
                for md_file in category_dir.glob("*.md"):
                    content = md_file.read_text(encoding="utf-8")
                    await graphiti.add_episode(
                        content,
                        metadata={"category": category_dir.name,
                                  "source": str(md_file)},
                    )
                    logger.info(f"  Added episode: {md_file.name}")
            await graphiti.close()
        except ImportError:
            logger.warning("graphiti-core not installed, skipping Graphiti ingestion")

    provider = config.graph_provider
    if provider == "mem0":
        logger.info("Re-ingestion complete! Mem0 graph extraction is async — "
                     "relations will appear in search results shortly.")
    elif provider == "graphiti":
        logger.info("Re-ingestion complete! Graphiti episodes ingested.")
    else:
        logger.info("Re-ingestion complete (no graph provider configured).")


if __name__ == "__main__":
    asyncio.run(reingest())
