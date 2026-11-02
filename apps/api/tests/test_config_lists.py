"""List settings accept JSON or comma-separated values (as .env files write them)."""

from src.core.config import Settings


def test_comma_separated(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a.test, http://b.test")
    monkeypatch.setenv("PLATFORM_ADMIN_EMAILS", "ops@x.test")
    s = Settings()
    assert s.cors_origins == ["http://a.test", "http://b.test"]
    assert s.platform_admin_emails == ["ops@x.test"]


def test_json(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["http://a.test"]')
    monkeypatch.setenv("PLATFORM_ADMIN_EMAILS", "[]")
    s = Settings()
    assert s.cors_origins == ["http://a.test"]
    assert s.platform_admin_emails == []


def test_configured_database_url_only_when_set(monkeypatch, tmp_path):
    from src.core import config

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(config.Settings, "model_config", {**config.Settings.model_config, "env_file": ()})
    assert config.configured_database_url() is None  # alembic.ini decides
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.test:5432/x")
    assert config.configured_database_url() == "postgresql://u:p@db.test:5432/x"
