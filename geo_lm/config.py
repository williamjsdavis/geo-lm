"""Configuration management for geo-lm using pydantic-settings."""

import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="GEO_LM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_path: str = "./data/geo_lm.db"

    # LLM Providers
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    llama_api_key: Optional[str] = None

    # Default Models
    default_model: str = "claude-sonnet-4-20250514"
    default_consolidation_model: str = "claude-sonnet-4-20250514"
    default_dsl_model: str = "claude-sonnet-4-20250514"
    default_embedding_model: str = "text-embedding-3-small"

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # Workflow Settings
    max_dsl_retries: int = 5
    llm_temperature: float = 0.7

    # Storage
    uploads_dir: str = "./uploads"
    exports_dir: str = "./exports"
    data_dir: str = "./data"

    def get_llm_api_key(self, provider: str = "anthropic") -> Optional[str]:
        """Get API key for the specified provider."""
        if provider == "anthropic":
            return self.anthropic_api_key
        elif provider == "openai":
            return self.openai_api_key
        elif provider == "llama":
            return self.llama_api_key or os.environ.get("LLAMA_API_KEY")
        return None

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        for dir_path in [self.uploads_dir, self.exports_dir, self.data_dir]:
            os.makedirs(dir_path, exist_ok=True)


# Global settings instance
settings = Settings()
