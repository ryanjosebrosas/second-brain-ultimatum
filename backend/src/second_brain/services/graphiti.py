"""Graph memory via Graphiti (Neo4j/FalkorDB backend)."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from second_brain.config import BrainConfig

logger = logging.getLogger(__name__)

# Retry config for Graphiti network calls — transient errors only
_GRAPHITI_RETRY = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    retry=retry_if_exception_type((ConnectionError, OSError)),
    reraise=True,
)


class GraphitiService:
    """Knowledge graph service via Graphiti + Neo4j."""

    def __init__(self, config: BrainConfig):
        self.config = config
        self._client = None  # Lazy init (async)
        self._initialized = False
        self._init_failed = False
        self._backend: str | None = None
        self._timeout: int = getattr(config, "service_timeout_seconds", 15)

    async def _ensure_init(self) -> None:
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

    def _build_providers(self) -> tuple[Any, Any, Any]:
        """Build LLM, embedder, and cross-encoder providers."""
        from graphiti_core.llm_client.config import LLMConfig

        # LLM: Anthropic primary -> Ollama (local or cloud) fallback
        # graphiti_llm_model overrides the default model selection
        llm_model_override = self.config.graphiti_llm_model

        if self.config.anthropic_api_key and not llm_model_override:
            from graphiti_core.llm_client.anthropic_client import AnthropicClient

            model_name = self.config.primary_model
            if model_name.startswith("anthropic:"):
                model_name = model_name[len("anthropic:"):]
            llm_client = AnthropicClient(
                config=LLMConfig(
                    api_key=self.config.anthropic_api_key,
                    model=model_name,
                )
            )
            logger.info("Graphiti using Anthropic LLM (%s)", model_name)
        else:
            from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient

            ollama_model = llm_model_override or self.config.ollama_model
            llm_config = LLMConfig(
                api_key=self.config.ollama_api_key or "ollama",
                model=ollama_model,
                small_model=ollama_model,
                base_url=f"{self.config.ollama_base_url}/v1",
            )
            llm_client = OpenAIGenericClient(config=llm_config)
            logger.info("Graphiti using Ollama LLM (%s)", ollama_model)

        # Embedder: Voyage AI preferred, OpenAI fallback
        if self.config.voyage_api_key:
            from graphiti_core.embedder.voyage import VoyageAIEmbedder, VoyageAIEmbedderConfig

            embedder = VoyageAIEmbedder(
                config=VoyageAIEmbedderConfig(
                    api_key=self.config.voyage_api_key,
                    embedding_model=self.config.graphiti_embedding_model,
                )
            )
            logger.info("Graphiti using Voyage AI embedder (%s)", self.config.graphiti_embedding_model)
        else:
            from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig

            embedder = OpenAIEmbedder(
                config=OpenAIEmbedderConfig(
                    api_key=self.config.openai_api_key or "",
                    embedding_model="text-embedding-3-small",
                )
            )
            logger.info("Graphiti using OpenAI embedder (text-embedding-3-small)")

        # Cross-encoder: OpenAI preferred, Ollama fallback
        from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient

        if self.config.openai_api_key:
            cross_encoder_config = LLMConfig(
                api_key=self.config.openai_api_key,
                model="gpt-4.1-mini",
            )
            cross_encoder = OpenAIRerankerClient(config=cross_encoder_config)
            logger.info("Graphiti using OpenAI cross-encoder (gpt-4.1-mini)")
        else:
            reranker_model = llm_model_override or self.config.ollama_model
            cross_config = LLMConfig(
                api_key=self.config.ollama_api_key or "ollama",
                model=reranker_model,
                base_url=f"{self.config.ollama_base_url}/v1",
            )
            cross_encoder = OpenAIRerankerClient(config=cross_config)
            logger.info("Graphiti using Ollama cross-encoder (%s)", reranker_model)

        return llm_client, embedder, cross_encoder

    @_GRAPHITI_RETRY
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

            # Build descriptive episode name
            ep_hash = f"{hash(content) & 0xFFFFFFFF:08x}"
            if metadata:
                source_name = metadata.get("source", metadata.get("category", "brain"))
                ep_name = f"{source_name}_{ep_hash}"
            else:
                ep_name = f"episode_{ep_hash}"

            # Use metadata for richer source description
            source_desc = "second-brain"
            if metadata:
                parts = []
                if metadata.get("source"):
                    parts.append(metadata["source"])
                if metadata.get("category"):
                    parts.append(f"category:{metadata['category']}")
                if metadata.get("client"):
                    parts.append(f"client:{metadata['client']}")
                source_desc = " | ".join(parts) if parts else "second-brain"

            # Support explicit reference_time from metadata (e.g., transcript dates)
            ref_time = datetime.now(timezone.utc)
            if metadata and metadata.get("reference_time"):
                try:
                    ref_time = datetime.fromisoformat(metadata["reference_time"])
                except (ValueError, TypeError):
                    pass  # Fall back to now

            kwargs = {
                "name": ep_name,
                "episode_body": content,
                "source": EpisodeType.text,
                "source_description": source_desc,
                "reference_time": ref_time,
            }
            if group_id:
                kwargs["group_id"] = group_id

            async with asyncio.timeout(self._timeout * 2):
                await self._client.add_episode(**kwargs)
        except TimeoutError:
            logger.warning("Graphiti add_episode timed out after %ds", self._timeout * 2)
        except (ConnectionError, OSError):
            raise  # Let retry decorator handle
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

        sem = asyncio.Semaphore(3)  # Limit concurrent LLM/DB calls

        async def _add_one(ep: dict) -> bool:
            async with sem:
                try:
                    await self.add_episode(
                        content=ep["content"],
                        metadata=ep.get("metadata"),
                    )
                    return True
                except Exception as e:
                    logger.debug("Batch episode failed: %s", e)
                    return False

        results = await asyncio.gather(*[_add_one(ep) for ep in episodes])
        return sum(1 for r in results if r)

    async def add_episodes_chunked(
        self,
        content: str,
        metadata: dict | None = None,
        group_id: str | None = None,
        chunk_size: int = 4000,
        chunk_overlap: int = 200,
    ) -> int:
        """Split long content into contextual chunks and add as separate episodes.

        Each chunk is prefixed with a context summary derived from the full content.
        This produces richer entity/relationship extraction than a single large episode.

        Returns the count of successfully added episodes.
        """
        await self._ensure_init()
        if not self._initialized:
            logger.debug("Graphiti not available, skipping chunked add")
            return 0

        if len(content) <= chunk_size:
            await self.add_episode(content, metadata=metadata, group_id=group_id)
            return 1

        # Build context prefix from first ~500 chars
        context_prefix = content[:500].rsplit(" ", 1)[0]
        context_line = f"[Context: {context_prefix}...]\n\n"

        # Chunk with overlap
        chunks = []
        start = 0
        while start < len(content):
            end = start + chunk_size
            # Try to break at sentence boundary
            if end < len(content):
                for sep in [". ", ".\n", "\n\n", "\n", " "]:
                    boundary = content[start:end].rfind(sep)
                    if boundary > chunk_size * 0.5:
                        end = start + boundary + len(sep)
                        break
            chunks.append(content[start:end])
            start = end - chunk_overlap

        added = 0
        for i, chunk in enumerate(chunks):
            chunk_meta = dict(metadata) if metadata else {}
            chunk_meta["chunk_index"] = i
            chunk_meta["total_chunks"] = len(chunks)

            # Prefix with context for better entity extraction
            episode_content = context_line + chunk if i > 0 else chunk

            try:
                await self.add_episode(
                    content=episode_content,
                    metadata=chunk_meta,
                    group_id=group_id,
                )
                added += 1
            except Exception as e:
                logger.debug("Chunked episode %d/%d failed: %s", i + 1, len(chunks), e)

        logger.info("Added %d/%d chunked episodes", added, len(chunks))
        return added

    @_GRAPHITI_RETRY
    async def search(
        self, query: str, limit: int = 10, group_id: str | None = None
    ) -> list[dict]:
        """Search graph for entity relationships."""
        await self._ensure_init()
        if not self._initialized:
            return []

        try:
            async with asyncio.timeout(self._timeout):
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
        except TimeoutError:
            logger.warning("Graphiti search timed out after %ds", self._timeout)
            return []
        except (ConnectionError, OSError):
            raise  # Let retry decorator handle
        except Exception as e:
            logger.warning("Graphiti search failed: %s", type(e).__name__)
            logger.debug("Graphiti search error detail: %s", e)
            return []

    @_GRAPHITI_RETRY
    async def search_entities(
        self, query: str, limit: int = 10, group_id: str | None = None
    ) -> list[dict]:
        """Search for entity nodes matching a query string.

        Returns list of entity dicts with name, uuid, summary, labels.
        """
        await self._ensure_init()
        if not self._initialized:
            return []
        try:
            driver = getattr(self._client, "driver", None)
            if driver is None:
                logger.warning("Graphiti search_entities: no driver available")
                return []

            # Try Entity label first (graphiti-core standard), fall back to EntityNode
            for label in ("Entity", "EntityNode"):
                try:
                    if group_id:
                        cypher = (
                            f"MATCH (e:{label}) "
                            "WHERE e.group_id = $gid AND (toLower(e.name) CONTAINS toLower($q) "
                            "OR toLower(e.summary) CONTAINS toLower($q)) "
                            "RETURN e.uuid AS uuid, e.name AS name, "
                            "e.summary AS summary, e.labels AS labels, "
                            "e.created_at AS created_at "
                            "ORDER BY e.name LIMIT $lim"
                        )
                        params = {"gid": group_id, "q": query, "lim": limit}
                    else:
                        cypher = (
                            f"MATCH (e:{label}) "
                            "WHERE toLower(e.name) CONTAINS toLower($q) "
                            "OR toLower(e.summary) CONTAINS toLower($q) "
                            "RETURN e.uuid AS uuid, e.name AS name, "
                            "e.summary AS summary, e.labels AS labels, "
                            "e.created_at AS created_at "
                            "ORDER BY e.name LIMIT $lim"
                        )
                        params = {"q": query, "lim": limit}
                    async with asyncio.timeout(self._timeout):
                        records, _, _ = await driver.execute_query(cypher, **params)
                    if records:
                        return [
                            {
                                "uuid": str(r["uuid"]) if r["uuid"] else "",
                                "name": str(r["name"]) if r["name"] else "",
                                "summary": str(r["summary"]) if r["summary"] else "",
                                "labels": r["labels"] if r["labels"] else [],
                                "created_at": str(r["created_at"]) if r["created_at"] else None,
                            }
                            for r in records
                        ]
                except Exception:
                    continue  # Try next label
            return []
        except (ConnectionError, OSError):
            raise
        except TimeoutError:
            logger.warning("Graphiti search_entities timed out after %ds", self._timeout)
            return []
        except Exception as e:
            logger.warning("Graphiti search_entities failed: %s", type(e).__name__)
            logger.debug("Graphiti search_entities error detail: %s", e)
            return []

    @_GRAPHITI_RETRY
    async def get_entity_context(
        self, entity_uuid: str, limit: int = 20
    ) -> dict:
        """Get an entity's relationships and connected entities.

        Returns dict with entity info and its relationships (incoming + outgoing).
        """
        await self._ensure_init()
        if not self._initialized:
            return {"entity": None, "relationships": []}
        try:
            driver = getattr(self._client, "driver", None)
            if driver is None:
                return {"entity": None, "relationships": []}

            # Get entity info + outgoing and incoming relationships
            cypher = (
                "MATCH (e {uuid: $uuid}) "
                "OPTIONAL MATCH (e)-[r]->(t) "
                "WITH e, collect(DISTINCT {type: type(r), fact: r.fact, "
                "target_name: t.name, target_uuid: t.uuid, direction: 'outgoing'}) AS outgoing "
                "OPTIONAL MATCH (s)-[r2]->(e) "
                "RETURN e.uuid AS uuid, e.name AS name, e.summary AS summary, "
                "outgoing, "
                "collect(DISTINCT {type: type(r2), fact: r2.fact, "
                "source_name: s.name, source_uuid: s.uuid, direction: 'incoming'}) AS incoming "
                "LIMIT 1"
            )
            async with asyncio.timeout(self._timeout):
                records, _, _ = await driver.execute_query(cypher, uuid=entity_uuid)

            if not records:
                return {"entity": None, "relationships": []}

            r = records[0]
            entity = {
                "uuid": str(r["uuid"]) if r["uuid"] else "",
                "name": str(r["name"]) if r["name"] else "",
                "summary": str(r["summary"]) if r["summary"] else "",
            }
            relationships = []
            for rel in (r.get("outgoing") or [])[:limit]:
                if rel.get("target_name"):
                    relationships.append({
                        "direction": "outgoing",
                        "type": str(rel.get("type", "RELATES_TO")),
                        "fact": str(rel.get("fact", "")),
                        "connected_entity": str(rel.get("target_name", "")),
                        "connected_uuid": str(rel.get("target_uuid", "")),
                    })
            for rel in (r.get("incoming") or [])[:limit]:
                if rel.get("source_name"):
                    relationships.append({
                        "direction": "incoming",
                        "type": str(rel.get("type", "RELATES_TO")),
                        "fact": str(rel.get("fact", "")),
                        "connected_entity": str(rel.get("source_name", "")),
                        "connected_uuid": str(rel.get("source_uuid", "")),
                    })
            return {"entity": entity, "relationships": relationships}
        except (ConnectionError, OSError):
            raise
        except TimeoutError:
            logger.warning("Graphiti get_entity_context timed out after %ds", self._timeout)
            return {"entity": None, "relationships": []}
        except Exception as e:
            logger.warning("Graphiti get_entity_context failed: %s", type(e).__name__)
            logger.debug("Graphiti get_entity_context error detail: %s", e)
            return {"entity": None, "relationships": []}

    @_GRAPHITI_RETRY
    async def traverse_neighbors(
        self, entity_uuid: str, max_hops: int = 2, limit: int = 20
    ) -> list[dict]:
        """BFS traversal from a starting entity, up to max_hops away.

        Returns list of relationship dicts showing the path from origin.
        """
        await self._ensure_init()
        if not self._initialized:
            return []
        try:
            # Try graphiti-core's search_ with bfs_origin if available
            if hasattr(self._client, "search_"):
                try:
                    from graphiti_core.search.search_config import SearchConfig
                    config = SearchConfig(
                        bfs_origin_node_uuids=[entity_uuid],
                        limit=limit,
                    )
                    async with asyncio.timeout(self._timeout * 2):
                        raw = await self._client.search_("", search_config=config)
                    edges = getattr(raw, "edges", [])
                    return [
                        {
                            "source": getattr(e, "source_node_name", "?"),
                            "relationship": getattr(e, "fact", "?"),
                            "target": getattr(e, "target_node_name", "?"),
                        }
                        for e in edges[:limit]
                    ]
                except (ImportError, AttributeError, TypeError):
                    pass  # Fall through to Cypher fallback

            # Cypher fallback: variable-length path
            driver = getattr(self._client, "driver", None)
            if driver is None:
                return []
            cypher = (
                "MATCH (start {uuid: $uuid})-[r*1.." + str(min(max_hops, 5)) + "]->(end) "
                "WITH start, end, r "
                "UNWIND r AS rel "
                "WITH startNode(rel) AS s, rel, endNode(rel) AS t "
                "RETURN DISTINCT s.name AS source, type(rel) AS relationship, "
                "t.name AS target, rel.fact AS fact "
                "LIMIT $lim"
            )
            async with asyncio.timeout(self._timeout * 2):
                records, _, _ = await driver.execute_query(
                    cypher, uuid=entity_uuid, lim=limit
                )
            return [
                {
                    "source": str(r["source"]) if r["source"] else "?",
                    "relationship": str(r.get("fact") or r.get("relationship", "?")),
                    "target": str(r["target"]) if r["target"] else "?",
                }
                for r in records
            ]
        except (ConnectionError, OSError):
            raise
        except TimeoutError:
            logger.warning("Graphiti traverse_neighbors timed out after %ds", self._timeout * 2)
            return []
        except Exception as e:
            logger.warning("Graphiti traverse_neighbors failed: %s", type(e).__name__)
            logger.debug("Graphiti traverse_neighbors error detail: %s", e)
            return []

    @_GRAPHITI_RETRY
    async def search_communities(
        self, query: str, limit: int = 5, group_id: str | None = None
    ) -> list[dict]:
        """Search community summaries via graphiti-core search_ API.

        Communities are automatically detected clusters of related entities.
        Returns list of community dicts with name, summary, uuid.
        """
        await self._ensure_init()
        if not self._initialized:
            return []
        try:
            if not hasattr(self._client, "search_"):
                logger.debug("search_ not available, communities search unavailable")
                return []
            kwargs = {"num_results": limit}
            if group_id:
                kwargs["group_ids"] = [group_id]
            async with asyncio.timeout(self._timeout):
                raw = await self._client.search_(query, **kwargs)
            communities = getattr(raw, "communities", [])
            return [
                {
                    "uuid": str(getattr(c, "uuid", "")),
                    "name": str(getattr(c, "name", "")),
                    "summary": str(getattr(c, "summary", "")),
                }
                for c in communities[:limit]
            ]
        except (ConnectionError, OSError):
            raise
        except TimeoutError:
            logger.warning("Graphiti search_communities timed out after %ds", self._timeout)
            return []
        except Exception as e:
            logger.warning("Graphiti search_communities failed: %s", type(e).__name__)
            logger.debug("Graphiti search_communities error detail: %s", e)
            return []

    @_GRAPHITI_RETRY
    async def build_communities(self, group_id: str | None = None) -> list[dict]:
        """Trigger community detection on the graph.

        This is an expensive operation — call explicitly, not automatically.
        Returns list of community dicts with uuid, name, summary.
        """
        await self._ensure_init()
        if not self._initialized:
            return []
        try:
            if not hasattr(self._client, "build_communities_"):
                logger.debug("build_communities_ not available on graphiti client")
                return []
            kwargs = {}
            if group_id:
                kwargs["group_ids"] = [group_id]
            async with asyncio.timeout(self._timeout * 3):
                await self._client.build_communities_(**kwargs)
            # After building, search for all communities to return them
            return await self.search_communities("", group_id=group_id)
        except (ConnectionError, OSError):
            raise
        except TimeoutError:
            logger.warning(
                "Graphiti build_communities timed out after %ds", self._timeout * 3
            )
            return []
        except Exception as e:
            logger.warning("Graphiti build_communities failed: %s", type(e).__name__)
            logger.debug("Graphiti build_communities error detail: %s", e)
            return []

    @_GRAPHITI_RETRY
    async def advanced_search(
        self,
        query: str,
        limit: int = 10,
        group_id: str | None = None,
        node_labels: list[str] | None = None,
        edge_types: list[str] | None = None,
        created_after: str | None = None,
        created_before: str | None = None,
    ) -> dict:
        """Advanced search with type and temporal filters.

        Returns dict with edges, nodes, and communities from the search.
        """
        await self._ensure_init()
        if not self._initialized:
            return {"edges": [], "nodes": [], "communities": []}
        try:
            if not hasattr(self._client, "search_"):
                # Fall back to basic search
                edges = await self.search(query, limit=limit, group_id=group_id)
                return {"edges": edges, "nodes": [], "communities": []}

            kwargs = {"num_results": limit}
            if group_id:
                kwargs["group_ids"] = [group_id]

            # Build search filters if any filter params provided
            if node_labels or edge_types or created_after or created_before:
                try:
                    from graphiti_core.search.search_config import SearchFilters
                    filter_kwargs = {}
                    if node_labels:
                        filter_kwargs["node_labels"] = node_labels
                    if edge_types:
                        filter_kwargs["edge_types"] = edge_types
                    if created_after:
                        filter_kwargs["created_at_start"] = datetime.fromisoformat(created_after)
                    if created_before:
                        filter_kwargs["created_at_end"] = datetime.fromisoformat(created_before)
                    kwargs["search_filters"] = SearchFilters(**filter_kwargs)
                except (ImportError, TypeError) as e:
                    logger.debug("SearchFilters not available: %s", e)

            async with asyncio.timeout(self._timeout):
                raw = await self._client.search_(query, **kwargs)

            edges = [
                {
                    "source": getattr(e, "source_node_name", "?"),
                    "relationship": getattr(e, "fact", "?"),
                    "target": getattr(e, "target_node_name", "?"),
                    "uuid": str(getattr(e, "uuid", "")),
                }
                for e in getattr(raw, "edges", [])[:limit]
            ]
            nodes = [
                {
                    "uuid": str(getattr(n, "uuid", "")),
                    "name": str(getattr(n, "name", "")),
                    "summary": str(getattr(n, "summary", "")),
                }
                for n in getattr(raw, "nodes", [])[:limit]
            ]
            communities = [
                {
                    "uuid": str(getattr(c, "uuid", "")),
                    "name": str(getattr(c, "name", "")),
                    "summary": str(getattr(c, "summary", "")),
                }
                for c in getattr(raw, "communities", [])[:limit]
            ]
            return {"edges": edges, "nodes": nodes, "communities": communities}
        except (ConnectionError, OSError):
            raise
        except TimeoutError:
            logger.warning("Graphiti advanced_search timed out after %ds", self._timeout)
            return {"edges": [], "nodes": [], "communities": []}
        except Exception as e:
            logger.warning("Graphiti advanced_search failed: %s", type(e).__name__)
            logger.debug("Graphiti advanced_search error detail: %s", e)
            return {"edges": [], "nodes": [], "communities": []}

    @_GRAPHITI_RETRY
    async def remove_episode(self, episode_uuid: str) -> bool:
        """Delete an episode node by UUID via Cypher query. Returns True on success."""
        await self._ensure_init()
        if not self._initialized:
            return False
        try:
            driver = getattr(self._client, "driver", None)
            if driver is None:
                logger.warning("Graphiti remove_episode: no driver available")
                return False
            async with asyncio.timeout(self._timeout):
                records, _, _ = await driver.execute_query(
                    "MATCH (e:EpisodicNode {uuid: $uuid}) DETACH DELETE e RETURN count(e) AS deleted",
                    uuid=episode_uuid,
                )
            deleted = records[0]["deleted"] if records else 0
            if deleted > 0:
                logger.debug("Removed episode %s", episode_uuid)
            return deleted > 0
        except TimeoutError:
            logger.warning("Graphiti remove_episode timed out after %ds", self._timeout)
            return False
        except (ConnectionError, OSError):
            raise  # Let retry decorator handle
        except Exception as e:
            logger.warning("Graphiti remove_episode failed: %s", type(e).__name__)
            logger.debug("Graphiti error detail: %s", e)
            return False

    @_GRAPHITI_RETRY
    async def get_episodes(self, group_id: str | None = None) -> list[dict]:
        """Retrieve all episodes, optionally filtered by group_id, via Cypher query."""
        await self._ensure_init()
        if not self._initialized:
            return []
        try:
            driver = getattr(self._client, "driver", None)
            if driver is None:
                logger.warning("Graphiti get_episodes: no driver available")
                return []
            if group_id:
                query = (
                    "MATCH (e:EpisodicNode {group_id: $gid}) "
                    "RETURN e.uuid AS id, e.content AS content, "
                    "e.source AS source, e.created_at AS created_at "
                    "ORDER BY e.created_at DESC LIMIT 1000"
                )
                params = {"gid": group_id}
            else:
                query = (
                    "MATCH (e:EpisodicNode) "
                    "RETURN e.uuid AS id, e.content AS content, "
                    "e.source AS source, e.created_at AS created_at "
                    "ORDER BY e.created_at DESC LIMIT 1000"
                )
                params = {}
            async with asyncio.timeout(self._timeout):
                records, _, _ = await driver.execute_query(query, **params)
            return [
                {
                    "id": str(r["id"]) if r["id"] else "",
                    "content": str(r["content"]) if r["content"] else "",
                    "source": str(r["source"]) if r["source"] else "unknown",
                    "created_at": str(r["created_at"]) if r["created_at"] else None,
                }
                for r in records
            ]
        except TimeoutError:
            logger.warning("Graphiti get_episodes timed out after %ds", self._timeout)
            return []
        except (ConnectionError, OSError):
            raise  # Let retry decorator handle
        except Exception as e:
            logger.warning("Graphiti get_episodes failed: %s", type(e).__name__)
            logger.debug("Graphiti error detail: %s", e)
            return []

    @_GRAPHITI_RETRY
    async def get_episode_by_id(self, episode_uuid: str) -> dict | None:
        """Retrieve a single episode by UUID via Cypher. Returns None if not found."""
        await self._ensure_init()
        if not self._initialized:
            return None
        try:
            driver = getattr(self._client, "driver", None)
            if driver is None:
                logger.warning("Graphiti get_episode_by_id: no driver available")
                return None
            async with asyncio.timeout(self._timeout):
                records, _, _ = await driver.execute_query(
                    "MATCH (e:EpisodicNode {uuid: $uuid}) "
                    "RETURN e.uuid AS id, e.content AS content, "
                    "e.source AS source, e.created_at AS created_at "
                    "LIMIT 1",
                    uuid=episode_uuid,
                )
            if not records:
                return None
            r = records[0]
            return {
                "id": str(r["id"]) if r["id"] else "",
                "content": str(r["content"]) if r["content"] else "",
                "source": str(r["source"]) if r["source"] else "unknown",
                "created_at": str(r["created_at"]) if r["created_at"] else None,
            }
        except (ConnectionError, OSError):
            raise
        except TimeoutError:
            logger.warning("Graphiti get_episode_by_id timed out after %ds", self._timeout)
            return None
        except Exception as e:
            logger.warning("Graphiti get_episode_by_id failed: %s", type(e).__name__)
            logger.debug("Graphiti get_episode_by_id error detail: %s", e)
            return None

    @_GRAPHITI_RETRY
    async def get_episode_count(self, group_id: str | None = None) -> int:
        """Count episodes for a group using efficient COUNT query."""
        await self._ensure_init()
        if not self._initialized:
            return 0
        try:
            driver = getattr(self._client, "driver", None)
            if driver is None:
                logger.warning("Graphiti get_episode_count: no driver available")
                return 0
            if group_id:
                query = "MATCH (e:EpisodicNode {group_id: $gid}) RETURN count(e) AS cnt"
                params = {"gid": group_id}
            else:
                query = "MATCH (e:EpisodicNode) RETURN count(e) AS cnt"
                params = {}
            async with asyncio.timeout(self._timeout):
                records, _, _ = await driver.execute_query(query, **params)
            return records[0]["cnt"] if records else 0
        except (ConnectionError, OSError):
            raise  # Let retry handle
        except TimeoutError:
            logger.warning("Graphiti get_episode_count timed out after %ds", self._timeout)
            return 0
        except Exception as e:
            logger.warning("Graphiti get_episode_count failed: %s", type(e).__name__)
            logger.debug("Graphiti get_episode_count error detail: %s", e)
            return 0

    @_GRAPHITI_RETRY
    async def delete_group_data(self, group_id: str) -> int:
        """Delete all episode data for a group_id. Returns count of deleted items."""
        await self._ensure_init()
        if not self._initialized:
            return 0
        try:
            driver = getattr(self._client, "driver", None)
            if driver is None:
                logger.warning("Graphiti delete_group_data: no driver available")
                return 0
            async with asyncio.timeout(self._timeout * 2):
                records, _, _ = await driver.execute_query(
                    "MATCH (e:EpisodicNode {group_id: $gid}) "
                    "WITH e, count(e) AS cnt "
                    "DETACH DELETE e "
                    "RETURN sum(cnt) AS deleted",
                    gid=group_id,
                )
            deleted = records[0]["deleted"] if records else 0
            logger.debug("Deleted %d episodes for group %s", deleted, group_id)
            return deleted
        except TimeoutError:
            logger.warning("Graphiti delete_group_data timed out after %ds", self._timeout * 2)
            return 0
        except (ConnectionError, OSError):
            raise  # Let retry decorator handle
        except Exception as e:
            logger.warning("Graphiti delete_group_data failed: %s", type(e).__name__)
            logger.debug("Graphiti error detail: %s", e)
            return 0

    async def close(self) -> None:
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

    @_GRAPHITI_RETRY
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
            async with asyncio.timeout(self._timeout):
                await self._client.search("health check", num_results=1)
            return {
                "status": "healthy",
                "backend": self._backend or "unknown",
            }
        except (ConnectionError, OSError):
            raise  # Let retry decorator handle
        except Exception as e:
            return {
                "status": "degraded",
                "backend": self._backend or "unknown",
                "error": str(e),
            }
