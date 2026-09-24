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
