"""Application configuration via pydantic-settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration is read from environment variables (or a .env file)."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # -- MongoDB --
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "agentic_search"

    # -- LLM --
    llm_provider: str = "anthropic"  # anthropic | openai
    llm_ingestion_model: str = "claude-3-5-haiku-20241022"
    llm_retrieval_model: str = "claude-sonnet-4-20250514"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""

    # -- Ingestion --
    max_pages_per_node: int = 10
    max_tokens_per_node: int = 20000
    toc_check_pages: int = 20
    generate_summaries: bool = True
    generate_keywords: bool = True

    # -- Retrieval --
    max_retrieval_iterations: int = 5
    atlas_search_weight: float = 0.3
    tree_navigation_weight: float = 0.7
    top_n_candidates: int = 5

    # -- API --
    port: int = 8000
    log_level: str = "info"
    cors_origins: str = ""  # comma-separated origins; empty = no CORS


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()
