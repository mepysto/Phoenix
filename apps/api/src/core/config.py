from functools import lru_cache

from pydantic import model_validator
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

    api_sync_key: str = DEV_SYNC_KEY

    cors_origins: list[str] = ["http://localhost:23000", "http://127.0.0.1:23000"]

    gdacs_api_url: str = "https://www.gdacs.org/gdacsapi/api"
    copernicus_api_url: str = "https://emergency.copernicus.eu"
    hdx_api_url: str = "https://data.humdata.org/api/3"

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
