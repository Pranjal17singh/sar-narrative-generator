"""Configuration management for SAR Narrative Generator."""

from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    # Application
    app_name: str = "SAR Narrative Generator"
    debug: bool = True

    # Database - PostgreSQL
    database_url: str = Field(
        default="postgresql://saruser:sarpass@localhost:5432/sar_db",
        alias="DATABASE_URL"
    )

    # Paths
    base_dir: Path = Path(__file__).parent.parent
    vector_store_path: Path = base_dir / "vector_store"
    data_samples_path: Path = base_dir / "data_samples"
    prompts_path: Path = base_dir / "prompts"

    # Ollama LLM Settings
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        alias="OLLAMA_BASE_URL"
    )
    ollama_model: str = Field(
        default="mistral",
        alias="OLLAMA_MODEL"
    )
    ollama_timeout: int = 180  # 3 minutes for first model load

    # RAG Settings
    embedding_model: str = "all-MiniLM-L6-v2"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k_retrieval: int = 5

    # Pattern Detection Thresholds
    structuring_threshold: float = 10000.0  # CTR threshold
    velocity_spike_multiplier: float = 3.0
    round_amount_threshold: float = 100.0
    rapid_movement_hours: int = 24

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
