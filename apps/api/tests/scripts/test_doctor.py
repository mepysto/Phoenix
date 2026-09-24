"""pnpm doctor must report key presence without ever printing values."""

import scripts.doctor as doctor
from scripts.doctor import FAIL, OK, WARN, check_keys, check_toolchain


def test_set_key_reports_presence_not_value(monkeypatch) -> None:
    monkeypatch.setattr(doctor, "OPTIONAL_KEYS", {"FIRMS_MAP_KEY": "example"})
    monkeypatch.setenv("FIRMS_MAP_KEY", "super-secret-value-123")
    output = "\n".join(str(r) for r in check_keys())
    assert "set" in output
    assert "super-secret-value-123" not in output
    assert all(r.status == OK for r in check_keys())


def test_missing_key_is_a_warning_not_a_failure(monkeypatch) -> None:
    monkeypatch.setattr(doctor, "OPTIONAL_KEYS", {"FIRMS_MAP_KEY": "example"})
    monkeypatch.delenv("FIRMS_MAP_KEY", raising=False)
    assert {r.status for r in check_keys()} == {WARN}


def test_toolchain_reports_python() -> None:
    python = next(r for r in check_toolchain() if r.name == "Python")
    assert python.status in {OK, FAIL}


def test_no_keys_needed_is_reported_ok(monkeypatch) -> None:
    monkeypatch.setattr(doctor, "OPTIONAL_KEYS", {})
    assert [r.status for r in check_keys()] == [OK]


def test_key_from_app_settings_counts_as_set(monkeypatch) -> None:
    """Keys in the API's .env reach the app through settings, not the environment."""
    from pydantic import SecretStr

    from src.core.config import get_settings

    monkeypatch.setattr(doctor, "OPTIONAL_KEYS", {"AISSTREAM_API_KEY": "ships"})
    monkeypatch.delenv("AISSTREAM_API_KEY", raising=False)
    monkeypatch.setattr(get_settings(), "aisstream_api_key", SecretStr("from-dotenv"))
    results = check_keys()
    assert [r.status for r in results] == [OK]
    assert "from-dotenv" not in "\n".join(str(r) for r in results)
