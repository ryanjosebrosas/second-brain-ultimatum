from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class BrainConfig(BaseSettings):
    """Configuration for the AI Second Brain."""

    # LLM providers
    anthropic_api_key: str | None = Field(
        default=None, description="Anthropic API key (None = skip, use Ollama)"
    )
    openai_api_key: str | None = Field(
        default=None, description="OpenAI API key for Mem0 embeddings"
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL",
    )
    ollama_api_key: str | None = Field(
        default=None, description="Ollama API key for cloud access"
    )
    ollama_model: str = Field(
        default="llama3.1:8b",
        description="Default Ollama model",
    )

    # Mem0
    mem0_api_key: Optional[str] = Field(
        default=None,
        description="Mem0 Cloud API key (None = use local)",
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
    )

    # Supabase
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_key: str = Field(..., description="Supabase anon key")

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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
