"""
etl/config/settings.py
======================
Configuration settings for the ETL pipeline.
Loads from environment variables / .env using pydantic-settings.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Base project path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class EtlSettings(BaseSettings):
    """ETL pipeline runtime settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Mock API Source Configuration
    mock_api_base_url: str = "http://localhost:8001"
    mock_api_key: str = "mock-api-key-change-in-prod"
    mock_api_page_size: int = 100

    # Retry and Network Policy
    max_retries: int = 3
    retry_min_wait_seconds: float = 1.0
    retry_max_wait_seconds: float = 10.0
    request_timeout_seconds: float = 30.0

    # Storage Paths
    data_dir: Path = PROJECT_ROOT / "data"
    state_file_path: Path = PROJECT_ROOT / "data" / "state" / "etl_state.json"
    raw_landing_dir: Path = PROJECT_ROOT / "data" / "raw"
    processed_dir: Path = PROJECT_ROOT / "data" / "processed"
    quarantine_dir: Path = PROJECT_ROOT / "data" / "quarantine"
    staging_dir: Path = PROJECT_ROOT / "data" / "staging"


settings = EtlSettings()
