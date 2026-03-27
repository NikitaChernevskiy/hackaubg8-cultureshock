"""Application configuration — loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for CultureShock API."""

    # --- App ---
    app_name: str = "CultureShock API"
    app_version: str = "0.1.0"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- CORS (lock down in production) ---
    cors_origins: list[str] = ["*"]

    # --- Azure OpenAI ---
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-12-01-preview"

    # --- SMS (Azure Communication Services) ---
    azure_comm_connection_string: str = ""
    azure_comm_from_number: str = ""

    # --- Firebase Push Notifications ---
    firebase_credentials_path: str = ""

    # --- Provider selection (swap mock ↔ real) ---
    alert_provider: str = "mock"        # mock | gdacs
    transport_provider: str = "mock"    # mock | google_maps
    ai_provider: str = "mock"           # mock | azure_openai
    notification_provider: str = "mock" # mock | azure_sms | firebase

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
