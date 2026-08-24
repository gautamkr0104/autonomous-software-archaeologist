"""Application settings loaded from environment variables."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for ASA.  All values can be overridden via env vars."""

    # --- Application ---
    app_name: str = "ASA"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # --- Paths ---
    data_dir: Path = Field(default=Path("D:/asa/data"), description="Base data directory")
    repos_dir: Path = Field(default=Path("D:/asa/data/repos"), description="Cloned repositories")
    cache_dir: Path = Field(default=Path("D:/asa/data/cache"), description="Cache directory")
    exports_dir: Path = Field(default=Path("D:/asa/data/exports"), description="Report exports")

    # --- Database ---
    database_url: str = Field(
        default="sqlite+aiosqlite:///D:/asa/data/asa.db",
        description="SQLAlchemy database URL",
    )
    database_echo: bool = False

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # --- Docker sandbox ---
    docker_enabled: bool = True
    docker_image: str = "python:3.11-slim"
    docker_network: str = "asa-isolated"
    docker_timeout: int = 300  # seconds
    docker_memory_limit: str = "512m"
    docker_cpu_limit: float = 1.0

    # --- Repository limits ---
    max_repo_size_mb: int = 500
    max_file_size_mb: int = 50
    max_files_analyzed: int = 10_000
    clone_timeout: int = 120  # seconds

    # --- LLM ---
    llm_provider: Literal["openai", "anthropic", "disabled"] = "disabled"
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-opus-20240229"
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.1

    # --- Agent limits ---
    agent_max_iterations: int = 10
    agent_max_token_budget: int = 100_000
    agent_timeout_seconds: int = 600

    # --- Security ---
    secret_key: str = "change-me-in-production"
    allowed_hosts: list[str] = ["localhost", "127.0.0.1"]
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # --- GitHub ---
    github_token: str = ""
    github_webhook_secret: str = ""

    model_config = {"env_prefix": "ASA_", "env_file": ".env", "env_file_encoding": "utf-8"}

    @field_validator("data_dir", "repos_dir", "cache_dir", "exports_dir", mode="before")
    @classmethod
    def ensure_dirs(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
