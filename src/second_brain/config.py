from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class BrainConfig(BaseSettings):
    """Configuration for the AI Second Brain."""

    # LLM providers
    anthropic_api_key: str = Field(..., description="Anthropic API key")
    openai_api_key: str = Field(..., description="OpenAI API key for embeddings")
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL",
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
