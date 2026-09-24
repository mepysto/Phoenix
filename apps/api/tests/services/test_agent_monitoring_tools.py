"""Agent tools for monitoring features and the new map actions."""

from datetime import UTC, datetime

import pytest

from src.schemas.agent import MapContext
from src.services.agent import monitoring_tools
from src.services.agent.tools import ToolError, run_data_tool, validate_map_action
from src.services.cameras.caltrans import Camera
from src.services.tracks.satellites import Pass


class FakeEvents:
    session = None


@pytest.mark.asyncio
async def test_satellite_passes(monkeypatch):
    async def passes(lat, lng, start, hours, min_elevation):
        assert (lat, lng, hours, min_elevation) == (35.0, 139.0, 24, 30)
        t = datetime(2026, 9, 25, 1, 27, tzinfo=UTC)
        return [Pass("SENTINEL-2C", 60989, t, t, t, 75.2, True)]

    monkeypatch.setattr(monitoring_tools.satellite_service, "passes", passes)
    result = await run_data_tool("satellite_passes", {"lat": 35, "lng": 139}, FakeEvents(), MapContext())
    assert result == {"passes": [{"satellite": "SENTINEL-2C", "peak": "2026-09-25T01:27+00:00", "max_elevation_deg": 75.2, "daylight": True}]}


@pytest.mark.asyncio
async def test_nearby_cameras_and_bad_input(monkeypatch):
    camera = Camera("caltrans-d4-1", "TV102 -- I-580", 37.8, -122.2, "West", "I-580", "https://cwwp2.dot.ca.gov/x.jpg", 5)

    async def nearest(lat, lng, radius, limit):
        return [(camera, 0.44)]

    monkeypatch.setattr(monitoring_tools.caltrans_cameras, "nearest", nearest)
    result = await run_data_tool("nearby_cameras", {"lat": 37.8, "lng": -122.2}, FakeEvents(), MapContext())
    assert result["cameras"] == [{"id": "caltrans-d4-1", "name": "TV102 -- I-580", "direction": "West", "distance_km": 0.4}]
    with pytest.raises(ToolError, match="out of range"):
        await run_data_tool("nearby_cameras", {"lat": 95, "lng": 0}, FakeEvents(), MapContext())
    with pytest.raises(ToolError, match="numeric"):
        await run_data_tool("local_radio", {"lat": "north"}, FakeEvents(), MapContext())


def test_new_map_actions_are_validated():
    ctx = MapContext()
    assert validate_map_action("set_basemap", {"basemap": "satellite"}, ctx).basemap == "satellite"
    assert validate_map_action("set_view_mode", {"mode": "flir"}, ctx).mode == "flir"
    route = validate_map_action("show_route", {"start": {"lat": 38.0, "lng": 12.5}, "end": {"lat": 38.1, "lng": 13.3}}, ctx)
    assert route.mode == "auto" and route.end.lng == 13.3
    assert validate_map_action("open_camera", {"camera_id": "caltrans-d4-488", "name": "Tunnel"}, ctx).name == "Tunnel"
    for name, args in [
        ("set_basemap", {"basemap": "streets"}),
        ("set_view_mode", {"mode": "xray"}),
        ("open_camera", {"camera_id": "../../etc/passwd"}),
        ("show_route", {"start": {"lat": 91, "lng": 0}, "end": {"lat": 0, "lng": 0}}),
    ]:
        with pytest.raises(ToolError):
            validate_map_action(name, args, ctx)
