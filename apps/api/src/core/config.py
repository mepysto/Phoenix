import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# The repository root .env (written by scripts/setup.sh) and, for overrides,
# apps/api/.env. Later files win; real environment variables win over both.
def _env_files() -> tuple[Path, ...]:
    here = Path(__file__).resolve()
    api_dir = here.parents[2]  # apps/api locally, /app in the container
    # The repository root is only present in a checkout, not in the image
    root = next((p for p in here.parents if (p / "pnpm-workspace.yaml").is_file()), None)
    return ((root / ".env",) if root else ()) + (api_dir / ".env",)


_ENV_FILES = _env_files()


def _str_list(value: object) -> object:
    """Accept a JSON list or a comma-separated string for list settings."""
    if isinstance(value, str):
        text = value.strip()
        if text.startswith("["):
            return json.loads(text)
        return [part.strip() for part in text.split(",") if part.strip()]
    return value


DEV_SYNC_KEY = "dev-sync-key"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILES, env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://phoenix:phoenix@localhost:23154/phoenix_db"
    redis_url: str = "redis://localhost:23163"

    api_host: str = "0.0.0.0"
    api_port: int = 23180
    api_debug: bool = False
    # SQL statement logging (includes bound parameters) — never enable in production
    db_echo: bool = False
    environment: str = "development"
    # Run the ingestion scheduler in this process. Disable in tests and in
    # API-only replicas when a dedicated worker runs the scheduler.
    scheduler_enabled: bool = True

    api_sync_key: str = DEV_SYNC_KEY

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:23100", "http://127.0.0.1:23100"]
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

    # Conflict zones (M7, RESPONSIBLE_USE §3). Near active war/complex
    # emergency events (and operator-defined boxes), military aircraft and
    # ships are generalised to a ~100 km grid without identity ("grid") or
    # removed ("hide"). Off by default; turn on for any deployment where
    # near-real-time military positions could endanger people.
    conflict_zone_policy: Literal["off", "grid", "hide"] = "off"
    conflict_zone_radius_km: float = 150
    # Extra zones as [west, south, east, north] boxes, e.g. '[[22,44,40,53]]'
    conflict_zone_bboxes: list[list[float]] = []

    # Accounts (Phase 2: needs, offers, connections). Login is by emailed
    # one-time link; there are no passwords.
    public_web_url: str = "http://localhost:23100"
    # Platform operators who approve organisations, e.g. '["ops@example.org"]'
    platform_admin_emails: Annotated[list[str], NoDecode] = []
    magic_link_ttl_minutes: int = 15
    magic_link_max_per_hour: int = 5
    session_ttl_days: int = 30
    session_cookie_name: str = "phoenix_session"
    # Outgoing mail. Without SMTP_HOST, mail is written to the log instead
    # (development only: a production deployment must configure SMTP).
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from: str = "Phoenix <no-reply@localhost>"
    smtp_starttls: bool = True
    # Development convenience: return the login link in the API response so
    # the flow works without mail. Ignored when ENVIRONMENT=production.
    auth_dev_return_link: bool = False

    # Closed-tab alerts (Web Push). Off unless a VAPID key is set; generate
    # one with `python -m scripts.gen_vapid_keys`.
    vapid_private_key: SecretStr | None = None
    vapid_subject: str = "mailto:ops@example.org"

    @field_validator("cors_origins", "platform_admin_emails", mode="before")
    @classmethod
    def _lists(cls, value: object) -> object:
        return _str_list(value)

    @property
    def secure_cookies(self) -> bool:
        return self.public_web_url.startswith("https://")

    @model_validator(mode="after")
    def reject_insecure_production(self) -> "Settings":
        if self.environment == "production":
            if self.api_sync_key == DEV_SYNC_KEY or len(self.api_sync_key) < 24:
                raise ValueError("API_SYNC_KEY must be set to a strong secret in production")
            if self.api_debug or self.db_echo:
                raise ValueError("API_DEBUG/DB_ECHO must be disabled in production")
            if self.auth_dev_return_link:
                raise ValueError("AUTH_DEV_RETURN_LINK must be off in production")
        return self


def configured_database_url() -> str | None:
    """DATABASE_URL from the environment or a .env file, if either sets it.

    Migrations and the setup check use this before falling back to
    alembic.ini, so they reach the same database as the API.
    """
    s = Settings()
    return s.database_url if "database_url" in s.model_fields_set else None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
