"""Migrations must produce exactly the schema the models describe.

Runs only against a real PostGIS/TimescaleDB database:
    TEST_DATABASE_URL=postgresql://user:pass@host:port/db pytest tests/integration
The database is migrated in place; use a disposable one.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[2]
DB_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL not set")


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "DATABASE_URL": DB_URL or "", "PYTHONPATH": str(API_ROOT)}
    return subprocess.run(
        [sys.executable, *args], cwd=API_ROOT, env=env, capture_output=True, text=True
    )


def test_migrate_to_head_then_no_drift() -> None:
    migrate = _run("-m", "scripts.migrate")
    assert migrate.returncode == 0, migrate.stderr

    check = _run("-m", "alembic", "check")
    assert check.returncode == 0, check.stdout + check.stderr


def test_migrate_is_idempotent() -> None:
    first = _run("-m", "scripts.migrate")
    second = _run("-m", "scripts.migrate")
    assert first.returncode == 0 and second.returncode == 0, second.stderr
