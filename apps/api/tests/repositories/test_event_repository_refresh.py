"""Tests for EventRepository.update_if_better (same-source refresh) and coords."""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.event import GeoMethod, GeoPrecision, SeverityLevel
from src.repositories.event_repository import EventRepository, _pop_coord


def _existing_event(**overrides):
    base = {
        "id": "evt-1",
        "title": "Old title",
        "description": "desc",
        "latitude": 10.0,
        "longitude": 20.0,
        "region": "X",
        "severity": SeverityLevel.medium,
        "source_url": None,
        "geo_precision": GeoPrecision.approximate,
        "geo_method": GeoMethod.source_provided,
        "end_date": None,
        "is_active": True,
        "start_date": datetime(2026, 9, 24, 4, 54, tzinfo=UTC),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _repo(event):
    session = MagicMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    repo = EventRepository(session)
    repo.get_by_id = AsyncMock(return_value=event)
    return repo, session


def _applied_values(session) -> dict:
    stmt = session.execute.call_args.args[0]
    return {
        col.name: getattr(val, "value", val) for col, val in stmt._values.items()
    }


@pytest.mark.asyncio
async def test_status_fields_update_without_precision_improvement():
    """Closing an event at the source must propagate (the original bug)."""
    repo, session = _repo(_existing_event())
    end = datetime(2026, 9, 1, tzinfo=UTC)

    result = await repo.update_if_better(
        "evt-1",
        {
            "title": "New title",
            "severity": SeverityLevel.high,
            "end_date": end,
            "is_active": False,
            "lat": 10.0,
            "lng": 20.0,
            "geo_precision": GeoPrecision.approximate,
        },
    )

    assert result is not None
    values = _applied_values(session)
    assert values["title"] == "New title"
    assert values["severity"] == SeverityLevel.high
    assert values["end_date"] == end
    assert values["is_active"] is False
    # Same coordinates: location untouched
    assert "location" not in values


@pytest.mark.asyncio
async def test_worse_precision_does_not_move_location():
    repo, session = _repo(_existing_event(geo_precision=GeoPrecision.exact))

    await repo.update_if_better(
        "evt-1",
        {"title": "T2", "lat": 11.0, "lng": 21.0, "geo_precision": GeoPrecision.country},
    )

    values = _applied_values(session)
    assert values["title"] == "T2"
    assert "latitude" not in values and "location" not in values
    assert "geo_precision" not in values


@pytest.mark.asyncio
async def test_equal_or_better_precision_moves_location():
    repo, session = _repo(_existing_event())

    await repo.update_if_better(
        "evt-1", {"lat": 11.0, "lng": 21.0, "geo_precision": GeoPrecision.exact}
    )

    values = _applied_values(session)
    assert values["latitude"] == 11.0 and values["longitude"] == 21.0
    assert "location" in values
    assert values["geo_precision"] == GeoPrecision.exact


@pytest.mark.asyncio
async def test_no_changes_returns_none_and_skips_write():
    repo, session = _repo(_existing_event())

    result = await repo.update_if_better(
        "evt-1", {"title": "Old title", "description": None, "lat": 10.0, "lng": 20.0}
    )

    assert result is None
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_none_does_not_erase_existing_values():
    repo, session = _repo(_existing_event())

    await repo.update_if_better("evt-1", {"description": None, "title": "T"})

    assert "description" not in _applied_values(session)


def test_pop_coord_keeps_zero():
    """0.0 (equator / prime meridian) is a valid coordinate, not a missing one."""
    data = {"lat": 0.0, "longitude": 0.0}
    assert _pop_coord(data, "lat", "latitude") == 0.0
    assert _pop_coord(data, "lng", "longitude") == 0.0
    assert data == {}


@pytest.mark.asyncio
async def test_start_date_only_moves_earlier():
    """An onset that fell back to ingestion time is repaired, never pushed later."""
    repo, session = _repo(_existing_event())
    onset = datetime(2026, 9, 21, tzinfo=UTC)

    await repo.update_if_better("evt-1", {"start_date": onset})
    assert _applied_values(session)["start_date"] == onset

    repo, session = _repo(_existing_event(start_date=onset))
    result = await repo.update_if_better("evt-1", {"start_date": datetime(2026, 9, 23, tzinfo=UTC)})
    assert result is None
    session.execute.assert_not_called()
