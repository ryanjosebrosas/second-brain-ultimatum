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

    async def _ensure_init(self):
        """Lazy async initialization of Graphiti client."""
        if self._initialized:
            return
        try:
            from graphiti_core import Graphiti

            llm_client, embedder, cross_encoder = self._build_providers()

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
            logger.info("Graphiti client initialized with Neo4j")
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti: {e}")
            raise

    def _build_providers(self):
        """Build LLM, embedder, and cross-encoder providers."""
        from graphiti_core.llm_client.config import LLMConfig
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

        # LLM: try Anthropic, fall back to Ollama
        if self.config.anthropic_api_key:
            from graphiti_core.llm_client.anthropic_client import AnthropicClient

            llm_client = AnthropicClient(
                config=LLMConfig(
                    api_key=self.config.anthropic_api_key,
                    model="claude-sonnet-4-20250514",
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
            model="gpt-4.1-nano",
        )
        cross_encoder = OpenAIRerankerClient(config=cross_encoder_config)

        return llm_client, embedder, cross_encoder

    async def add_episode(
        self, content: str, metadata: dict | None = None
    ) -> None:
        """Add content as a graph episode for entity extraction."""
        await self._ensure_init()

        from graphiti_core.edges import EpisodeType

        source_desc = "second-brain"
        if metadata:
            source_desc = metadata.get("source", metadata.get("category", "second-brain"))

        await self._client.add_episode(
            name=f"episode_{hash(content) & 0xFFFFFFFF:08x}",
            episode_body=content,
            source=EpisodeType.text,
            source_description=source_desc,
            reference_time=datetime.now(timezone.utc),
        )

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        """Search graph for entity relationships."""
        await self._ensure_init()

        results = await self._client.search(query)
        relations = []
        for edge in results[:limit]:
            relations.append({
                "source": getattr(edge, "source_node_name", "?"),
                "relationship": getattr(edge, "fact", "?"),
                "target": getattr(edge, "target_node_name", "?"),
            })
        return relations

    async def close(self):
        """Close the Graphiti client connection."""
        if self._client:
            await self._client.close()
            self._initialized = False
