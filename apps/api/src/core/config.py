from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://phoenix:phoenix@localhost:5432/phoenix_db"
    redis_url: str = "redis://localhost:6379"

    api_host: str = "0.0.0.0"
    api_port: int = 28000
    api_debug: bool = True

    api_sync_key: str = "dev-sync-key"

    cors_origins: list[str] = ["http://localhost:23000", "http://127.0.0.1:23000"]

    gdacs_api_url: str = "https://www.gdacs.org/gdacsapi/api"
    copernicus_api_url: str = "https://emergency.copernicus.eu"
    hdx_api_url: str = "https://data.humdata.org/api/3"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
