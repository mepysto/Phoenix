"""Tests for database models, validations, and timezone defaults."""

import json
import pytest
from datetime import datetime, UTC
from uuid import uuid4

from src.models.event import Event, GeoLayer, Dataset, EventSource
from src.models.admin_area import AdminArea


@pytest.mark.parametrize("model", [AdminArea, Event])
@pytest.mark.parametrize("column", ["created_at", "updated_at"])
def test_timestamp_defaults_are_timezone_aware(model, column) -> None:
    """Column defaults must produce aware UTC datetimes (not naive utcnow)."""
    default = model.__table__.c[column].default
    assert default is not None and callable(default.arg)
    value = default.arg(None)
    assert value.tzinfo is not None
    assert value.utcoffset().total_seconds() == 0


def test_geolayer_geojson_validation() -> None:
    """Test GeoLayer's size and format validation for the geojson column."""
    layer = GeoLayer(
        layer_type="test_layer",
    )
    
    # Test valid dict GeoJSON
    valid_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [10.0, 20.0]
                },
                "properties": {"name": "test"}
            }
        ]
    }
    
    layer.geojson = valid_geojson
    assert layer.geojson == valid_geojson

    # Test valid JSON string GeoJSON (automatically parsed to dict)
    valid_json_string = json.dumps(valid_geojson)
    layer.geojson = valid_json_string
    assert layer.geojson == valid_geojson

    # Test invalid string format
    with pytest.raises(ValueError, match="Invalid JSON string in GeoJSON"):
        layer.geojson = "{invalid_json}"

    # Test invalid type (e.g. integer)
    with pytest.raises(ValueError, match="GeoJSON must be a dictionary or a valid JSON string"):
        layer.geojson = 12345


def test_geolayer_geojson_size_limit() -> None:
    """Test that GeoLayer correctly rejects payloads larger than 5MB."""
    layer = GeoLayer(
        layer_type="test_layer",
    )

    # 5MB + 10 bytes payload
    large_properties = "A" * (5 * 1024 * 1024 + 10)
    large_geojson = {
        "type": "FeatureCollection",
        "features": [],
        "properties": {
            "data": large_properties
        }
    }

    # Dict payload check
    with pytest.raises(ValueError, match="GeoJSON payload exceeds 5MB size limit"):
        layer.geojson = large_geojson

    # String payload check
    large_string = json.dumps(large_geojson)
    with pytest.raises(ValueError, match="GeoJSON payload exceeds 5MB size limit"):
        layer.geojson = large_string
