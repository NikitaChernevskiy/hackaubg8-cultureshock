"""Application configuration — loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for CultureShock API."""

    # --- App ---
    app_name: str = "Amygdala API"
    app_version: str = "1.0.0"
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

    # --- Twilio SMS ---
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    # --- Firebase Push Notifications ---
    firebase_credentials_path: str = ""

    # --- Provider selection (real by default, mock for testing) ---
    alert_provider: str = "multi"        # multi (USGS+GDACS+NASA+ReliefWeb) | usgs | mock
    transport_provider: str = "osm"      # osm (real OpenStreetMap) | mock
    ai_provider: str = "azure_openai"    # azure_openai | mock
    notification_provider: str = "mock"  # mock | azure_sms | firebase

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
