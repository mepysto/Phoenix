from functools import lru_cache

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEV_SYNC_KEY = "dev-sync-key"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://phoenix:phoenix@localhost:5432/phoenix_db"
    redis_url: str = "redis://localhost:6379"

    api_host: str = "0.0.0.0"
    api_port: int = 28000
    api_debug: bool = False
    # SQL statement logging (includes bound parameters) — never enable in production
    db_echo: bool = False
    environment: str = "development"
    # Run the ingestion scheduler in this process. Disable in tests and in
    # API-only replicas when a dedicated worker runs the scheduler.
    scheduler_enabled: bool = True

    api_sync_key: str = DEV_SYNC_KEY

    cors_origins: list[str] = ["http://localhost:23000", "http://127.0.0.1:23000"]
    # Upper bound on concurrent WebSocket clients per API process
    ws_max_connections: int = 1000

    gdacs_api_url: str = "https://www.gdacs.org/gdacsapi/api"
    copernicus_api_url: str = "https://emergency.copernicus.eu"
    hdx_api_url: str = "https://data.humdata.org/api/3"

    # Map agent (M4). Off unless a key is set: keys are upgrades, not gates.
    anthropic_api_key: SecretStr | None = None
    agent_model: str = "claude-sonnet-5"
    agent_max_output_tokens: int = 1024
    # Model calls per user message (each tool round trip is one)
    agent_max_steps: int = 6
    # Token caps (input + output). Session ids come from the client, so the
    # daily cap across all sessions is the real hard ceiling on spend.
    agent_session_token_cap: int = 200_000
    agent_daily_token_cap: int = 5_000_000

    # Ships (M5, AISStream). Off unless a key is set. One stream per
    # deployment (it runs where the scheduler runs); AISStream allows only
    # 3 connections per account.
    aisstream_api_key: SecretStr | None = None
    # Boxes watched around active high/critical events (degrees half-width)
    ais_max_boxes: int = 20
    ais_box_degrees: float = 3.0

    # Routing (M6, Valhalla). The FOSSGIS demo server allows fair use only,
    # asks apps to identify themselves (X-Client-Id) and caps the total
    # circumference of avoided areas at 10 km, which is too small to route
    # around disaster zones: self-host Valhalla and raise the cap for that.
    valhalla_url: str = "https://valhalla1.openstreetmap.de"
    valhalla_client_id: str = "phoenix-disaster-map"
    valhalla_max_exclude_circumference_m: float = 10_000

    @model_validator(mode="after")
    def reject_insecure_production(self) -> "Settings":
        if self.environment == "production":
            if self.api_sync_key == DEV_SYNC_KEY or len(self.api_sync_key) < 24:
                raise ValueError("API_SYNC_KEY must be set to a strong secret in production")
            if self.api_debug or self.db_echo:
                raise ValueError("API_DEBUG/DB_ECHO must be disabled in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
