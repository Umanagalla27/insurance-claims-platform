"""
mock_api/app/config.py
======================
Configuration settings for Mock External Insurance API.
Reads from environment variables / .env using pydantic-settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class MockApiSettings(BaseSettings):
    """Configuration for Mock External Core Insurance API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API Authentication
    mock_api_key: str = "mock-api-key-change-in-prod"

    # Server configuration
    mock_api_host: str = "0.0.0.0"
    mock_api_port: int = 8001

    # Rate Limiting: max requests per minute per client
    rate_limit_per_minute: int = 120

    # Chaos / Error Simulation (for testing downstream ETL retry mechanisms)
    simulate_errors: bool = False
    error_rate: float = 0.05  # 5% chance of transient 500/503 when simulation enabled


settings = MockApiSettings()
