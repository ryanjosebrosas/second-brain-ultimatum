import logging
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class BrainConfig(BaseSettings):
    """Configuration for the AI Second Brain."""

    # LLM providers
    anthropic_api_key: str | None = Field(
        default=None, description="Anthropic API key (None = skip, use Ollama)",
        repr=False,
    )
    openai_api_key: str | None = Field(
        default=None, description="OpenAI API key for Mem0 embeddings",
        repr=False,
    )

    # Embeddings
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model for vector search",
    )
    embedding_dimensions: int = Field(
        default=1536,
        ge=256,
        le=3072,
        description="Embedding vector dimensions. Must match DB schema vector(1536) column definition.",
    )
    embedding_batch_size: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Batch size for embedding generation during migration. Range: 1-200.",
    )

    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL",
    )
    ollama_api_key: str | None = Field(
        default=None, description="Ollama API key for cloud access",
        repr=False,
    )
    ollama_model: str = Field(
        default="llama3.1:8b",
        description="Default Ollama model",
    )

    # Subscription auth (Claude Pro/Max)
    use_subscription: bool = Field(
        default=False,
        description="Use Claude subscription (OAuth) instead of API key. "
        "Requires claude CLI installed and authenticated.",
    )
    claude_oauth_token: str | None = Field(
        default=None,
        description="OAuth token override. If not set, reads from credential store.",
        repr=False,
    )

    # Mem0
    mem0_api_key: str | None = Field(
        default=None,
        description="Mem0 Cloud API key (None = use local)",
        repr=False,
    )

    # Graph memory
    graph_provider: str = Field(
        default="none",
        description="Graph memory provider: none, mem0, or graphiti",
    )
    neo4j_url: str | None = Field(
        default=None,
        description="Neo4j connection URL (e.g., neo4j+s://xxx.databases.neo4j.io)",
    )
    neo4j_username: str | None = Field(
        default=None,
        description="Neo4j username",
    )
    neo4j_password: str | None = Field(
        default=None,
        description="Neo4j password",
        repr=False,
    )

    # Graphiti (independent of Mem0 graph)
    graphiti_enabled: bool = Field(
        default=False,
        description="Enable Graphiti knowledge graph (runs alongside Mem0 graph)",
    )
    falkordb_url: str | None = Field(
        default=None,
        description="FalkorDB connection URL (e.g., falkor://localhost:6379). Used as Graphiti fallback.",
    )
    falkordb_password: str | None = Field(
        default=None,
        description="FalkorDB password",
        repr=False,
    )

    # Supabase
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_key: str = Field(..., description="Supabase anon key", repr=False)

    # Brain
    brain_user_id: str = Field(default="ryan", description="Default user ID")
    brain_data_path: Path = Field(
        ...,
        description="Path to Second Brain markdown data",
    )

    # Model preferences
    primary_model: str = Field(
        default="anthropic:claude-sonnet-4-5",
        description="Primary Pydantic AI model string",
    )
    fallback_model: str = Field(
        default="ollama:llama3.1:8b",
        description="Fallback model when primary unavailable",
    )

    # Search limits
    memory_search_limit: int = Field(
        default=10, description="Default limit for semantic memory search results"
    )
    graph_search_limit: int = Field(
        default=5, description="Default limit for graph relationship search results"
    )
    pattern_context_limit: int = Field(
        default=30, description="Number of existing patterns injected into learn agent context"
    )
    experience_limit: int = Field(
        default=5, description="Default limit for experience retrieval"
    )

    # Graduation settings
    graduation_min_memories: int = Field(
        default=3,
        description="Minimum memories in a cluster to graduate to a pattern",
    )
    graduation_lookback_days: int = Field(
        default=30,
        description="Number of days of memories to consider for graduation",
    )

    # API timeouts
    api_timeout_seconds: int = Field(
        default=30,
        ge=5,
        le=300,
        description="Timeout in seconds for external API calls (Mem0, Supabase, LLM). Range: 5-300.",
    )

    mcp_review_timeout_multiplier: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Multiplier for review tool timeout (runs 6 parallel reviews). Range: 1-5.",
    )

    # Input validation
    max_input_length: int = Field(
        default=10000,
        description="Maximum character length for CLI/MCP text inputs",
    )

    # Display limits
    content_preview_limit: int = Field(
        default=1000, description="Character limit for content previews in agent context"
    )
    pattern_preview_limit: int = Field(
        default=200, description="Character limit for pattern text in search results"
    )

    @model_validator(mode="after")
    def _validate_graph_config(self) -> "BrainConfig":
        if self.graph_provider == "graphiti":
            missing = []
            if not self.neo4j_url:
                missing.append("NEO4J_URL")
            if not self.neo4j_username:
                missing.append("NEO4J_USERNAME")
            if not self.neo4j_password:
                missing.append("NEO4J_PASSWORD")
            if missing:
                raise ValueError(
                    f"graph_provider='graphiti' requires: {', '.join(missing)}"
                )
        # Graphiti independent validation
        if self.graphiti_enabled:
            if not self.neo4j_url and not self.falkordb_url:
                raise ValueError(
                    "graphiti_enabled=True requires at least one of: "
                    "NEO4J_URL or FALKORDB_URL"
                )
        return self

    @model_validator(mode="after")
    def _validate_subscription_config(self) -> "BrainConfig":
        if self.use_subscription:
            # Warn if API key is also set (subscription takes priority)
            if self.anthropic_api_key:
                logger.info(
                    "Both API key and subscription auth configured. "
                    "Subscription auth takes priority when USE_SUBSCRIPTION=true."
                )
        return self

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
