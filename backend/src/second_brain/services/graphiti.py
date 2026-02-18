"""Graph memory via Graphiti (Neo4j/FalkorDB backend)."""

import logging
from datetime import datetime, timezone

from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)


class GraphitiService:
    """Knowledge graph service via Graphiti + Neo4j."""

    def __init__(self, config: BrainConfig):
        self.config = config
        self._client = None  # Lazy init (async)
        self._initialized = False
        self._init_failed = False
        self._backend: str | None = None

    async def _ensure_init(self):
        """Lazy async initialization with Neo4j primary → FalkorDB fallback."""
        if self._initialized:
            return
        if self._client is None and self._init_failed:
            return

        from graphiti_core import Graphiti

        llm_client, embedder, cross_encoder = self._build_providers()

        # Try Neo4j primary
        if self.config.neo4j_url:
            try:
                self._client = Graphiti(
                    self.config.neo4j_url,
                    self.config.neo4j_username,
                    self.config.neo4j_password,
                    llm_client=llm_client,
                    embedder=embedder,
                    cross_encoder=cross_encoder,
                )
                await self._client.build_indices_and_constraints()
                self._initialized = True
                self._backend = "neo4j"
                logger.info("Graphiti initialized with Neo4j")
                return
            except Exception as e:
                logger.warning("Graphiti Neo4j init failed: %s — trying FalkorDB fallback", type(e).__name__)
                logger.debug("Neo4j init error: %s", e)
                self._client = None

        # Try FalkorDB fallback
        if self.config.falkordb_url:
            try:
                self._client = Graphiti(
                    self.config.falkordb_url,
                    password=self.config.falkordb_password,
                    llm_client=llm_client,
                    embedder=embedder,
                    cross_encoder=cross_encoder,
                )
                await self._client.build_indices_and_constraints()
                self._initialized = True
                self._backend = "falkordb"
                logger.info("Graphiti initialized with FalkorDB (fallback)")
                return
            except Exception as e:
                logger.warning("Graphiti FalkorDB fallback also failed: %s", type(e).__name__)
                logger.debug("FalkorDB init error: %s", e)
                self._client = None

        # Both failed
        logger.error("Graphiti initialization failed — no backend available")
        self._init_failed = True

    def _build_providers(self):
        """Build LLM, embedder, and cross-encoder providers."""
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

        # LLM: try Anthropic, fall back to Ollama
        if self.config.anthropic_api_key:
            from graphiti_core.llm_client.anthropic_client import AnthropicClient

            # Extract model name from config (strip "anthropic:" prefix if present)
            model_name = self.config.primary_model
            if model_name.startswith("anthropic:"):
                model_name = model_name[len("anthropic:"):]
            llm_client = AnthropicClient(
                config=LLMConfig(
                    api_key=self.config.anthropic_api_key,
                    model=model_name,
                )
            )
            logger.info("Graphiti using Anthropic LLM")
        else:
            from graphiti_core.llm_client.openai_generic_client import (
                OpenAIGenericClient,
            )

            llm_config = LLMConfig(
                api_key=self.config.ollama_api_key or "ollama",
                model=self.config.ollama_model,
                base_url=f"{self.config.ollama_base_url}/v1",
            )
            llm_client = OpenAIGenericClient(config=llm_config)
            logger.info(f"Graphiti using Ollama LLM: {self.config.ollama_model}")

        # Embedder: OpenAI (required for Graphiti)
        embedder = OpenAIEmbedder(
            config=OpenAIEmbedderConfig(
                api_key=self.config.openai_api_key or "",
                embedding_model="text-embedding-3-small",
            )
        )

        # Cross-encoder: OpenAI reranker for result quality
        from graphiti_core.cross_encoder.openai_reranker_client import (
            OpenAIRerankerClient,
        )

        cross_encoder_config = LLMConfig(
            api_key=self.config.openai_api_key or "",
            model="gpt-4.1-mini",
        )
        cross_encoder = OpenAIRerankerClient(config=cross_encoder_config)

        return llm_client, embedder, cross_encoder

    async def add_episode(
        self,
        content: str,
        metadata: dict | None = None,
        group_id: str | None = None,
    ) -> None:
        """Add content as a graph episode for entity extraction."""
        await self._ensure_init()
        if not self._initialized:
            logger.debug("Graphiti not available, skipping add_episode")
            return

        try:
            from graphiti_core.edges import EpisodeType

            source_desc = "second-brain"
            if metadata:
                source_desc = metadata.get("source", metadata.get("category", "second-brain"))

            kwargs = {
                "name": f"episode_{hash(content) & 0xFFFFFFFF:08x}",
                "episode_body": content,
                "source": EpisodeType.text,
                "source_description": source_desc,
                "reference_time": datetime.now(timezone.utc),
            }
            if group_id:
                kwargs["group_id"] = group_id

            await self._client.add_episode(**kwargs)
        except Exception as e:
            logger.warning("Graphiti add_episode failed: %s", type(e).__name__)
            logger.debug("Graphiti add_episode error detail: %s", e)

    async def add_episodes_batch(
        self, episodes: list[dict],
    ) -> int:
        """Add multiple episodes. Each dict must have 'content' and optionally 'metadata'.

        Returns the count of successfully added episodes.
        """
        await self._ensure_init()
        if not self._initialized:
            logger.debug("Graphiti not available, skipping batch add")
            return 0

        added = 0
        for ep in episodes:
            try:
                await self.add_episode(
                    content=ep["content"],
                    metadata=ep.get("metadata"),
                )
                added += 1
            except Exception as e:
                logger.debug("Batch episode failed: %s", e)
        return added

    async def search(
        self, query: str, limit: int = 10, group_id: str | None = None
    ) -> list[dict]:
        """Search graph for entity relationships."""
        await self._ensure_init()
        if not self._initialized:
            return []

        try:
            if group_id and hasattr(self._client, "search_"):
                raw = await self._client.search_(query, group_ids=[group_id])
                edges = getattr(raw, "edges", [])
            else:
                edges = await self._client.search(query)
            relations = []
            for edge in edges[:limit]:
                relations.append({
                    "source": getattr(edge, "source_node_name", "?"),
                    "relationship": getattr(edge, "fact", "?"),
                    "target": getattr(edge, "target_node_name", "?"),
                })
            return relations
        except Exception as e:
            logger.warning("Graphiti search failed: %s", type(e).__name__)
            logger.debug("Graphiti search error detail: %s", e)
            return []

    async def close(self):
        """Close the Graphiti client connection."""
        if self._client:
            await self._client.close()
            self._initialized = False

    @property
    def is_available(self) -> bool:
        """Check if Graphiti is initialized and ready."""
        return self._initialized and self._client is not None

    @property
    def backend(self) -> str:
        """Return the active backend name or 'none'."""
        return self._backend or "none"

    async def health_check(self) -> dict:
        """Check Graphiti connectivity and return status dict."""
        await self._ensure_init()
        if not self._initialized:
            return {
                "status": "unavailable",
                "backend": "none",
                "error": "initialization failed",
            }
        try:
            await self._client.search("health check", num_results=1)
            return {
                "status": "healthy",
                "backend": self._backend or "unknown",
            }
        except Exception as e:
            return {
                "status": "degraded",
                "backend": self._backend or "unknown",
                "error": str(e),
            }
