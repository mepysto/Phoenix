"""Conflict-zone policy for military positions."""

from src.services.tracks.conflict_policy import ConflictZones, apply_policy


def aircraft(lat, lng, military=True, callsign="RCH123"):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
        "properties": {"hex": "ae1234", "callsign": callsign, "military": military, "speed_kt": 450, "track_deg": 90},
    }


ZONES = ConflictZones(points=[(48.5, 35.0)], radius_km=150)  # a front line
is_military = lambda p: p.get("military") is True  # noqa: E731


def test_off_changes_nothing():
    features = [aircraft(48.6, 35.1)]
    assert apply_policy(features, "off", ZONES, is_military) == features


def test_grid_generalises_military_inside_zones_only():
    inside, outside, civil = aircraft(48.62, 35.37), aircraft(40.0, 20.0), aircraft(48.6, 35.1, military=False)
    result = apply_policy([inside, outside, civil], "grid", ZONES, is_military)
    assert result[0] == {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [35.5, 48.5]},  # centre of the 1-degree cell
        "properties": {"military": True, "generalised": True},  # no callsign, hex, speed or track
    }
    assert result[1] is outside and result[2] is civil


def test_hide_drops_military_inside_zones():
    result = apply_policy([aircraft(48.6, 35.1), aircraft(40.0, 20.0)], "hide", ZONES, is_military)
    assert [f["geometry"]["coordinates"] for f in result] == [[20.0, 40.0]]


def test_operator_boxes_including_across_the_antimeridian():
    zones = ConflictZones(boxes=[[170, -20, -170, 0]])
    assert zones.contains(-10, 175) and zones.contains(-10, -175)
    assert not zones.contains(-10, 160)
    assert ConflictZones(boxes=[[22, 44, 40, 53]]).contains(48.0, 30.0)


def test_zone_cache_loads_on_first_use_even_right_after_boot(monkeypatch):
    """Regression: monotonic time starts near 0 on fresh machines (CI runners)."""
    import asyncio

    from src.services.tracks import conflict_policy

    monkeypatch.setattr(conflict_policy.time, "monotonic", lambda: 12.0)  # 12 s after boot
    loaded = []

    class Session:
        async def execute(self, statement):
            loaded.append(statement)

            class Rows:
                def all(self):
                    return [(48.5, 35.0)]

            return Rows()

    zones = asyncio.run(conflict_policy.ConflictZoneCache().zones(Session(), 150, []))
    assert loaded and zones.points == [(48.5, 35.0)]
