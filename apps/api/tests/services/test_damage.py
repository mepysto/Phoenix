"""Copernicus damage grades and summaries."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from src.models.event import GeoLayer
from src.services.copernicus_service import DamageAssessment
from src.services.damage import normalize_grade, summarize, to_layers


@pytest.mark.parametrize(
    "raw,grade",
    [
        ("Destroyed", "destroyed"),
        ("Completely destroyed", "destroyed"),
        ("Damaged", "damaged"),
        ("Moderate damage", "damaged"),
        ("Possibly damaged", "possibly_damaged"),
        ("Possibly Damaged", "possibly_damaged"),
        ("No visible damage", "no_visible_damage"),
        ("Not affected", "no_visible_damage"),
        (None, "unknown"),
        ("", "unknown"),
        ("???", "unknown"),
    ],
)
def test_normalize_grade(raw, grade):
    assert normalize_grade(raw) == grade


def assessment(grade, geometry, area=1.0):
    return DamageAssessment(
        activation_code="EMSR900",
        aoi_id="1",
        aoi_name="Old town",
        product_type="GRA",
        geometry=geometry,
        damage_grade=grade,
        affected_area_km2=area,
        timestamp=datetime(2026, 10, 1, tzinfo=UTC),
        download_url="https://emergency.copernicus.eu/x.pdf",
    )


POINT = {"type": "Point", "coordinates": [91.9, 24.9]}


def test_invalid_geometry_is_skipped():
    rows = to_layers(uuid4(), [assessment("Damaged", POINT), assessment("Damaged", {"type": "Point", "coordinates": [500, 0]}), assessment("Damaged", {})])
    assert len(rows) == 1
    assert rows[0].properties["grade"] == "damaged"


def test_summary_counts_and_orders_worst_first():
    eid = uuid4()
    rows = to_layers(eid, [assessment("Possibly damaged", POINT, 2.5), assessment("Destroyed", POINT, 1.0), assessment("Destroyed", POINT, 0.5)])
    for r in rows:
        r.id = uuid4()
    s = summarize(eid, rows)
    assert s.total == 3
    assert s.by_grade["destroyed"] == 2
    assert s.area_km2_by_grade["destroyed"] == 1.5
    assert [a.grade for a in s.areas] == ["destroyed", "destroyed", "possibly_damaged"]
    assert s.activations == ["EMSR900"]


def test_only_https_links_are_exposed():
    eid = uuid4()
    layer = GeoLayer(id=uuid4(), event_id=eid, layer_type="damage", geojson=POINT, properties={"grade": "damaged", "url": "javascript:alert(1)"})
    assert summarize(eid, [layer]).areas[0].url is None
