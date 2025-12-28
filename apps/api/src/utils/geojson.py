"""
GeoJSON conversion and validation utilities.

This module provides utilities for converting events to GeoJSON format
and validating GeoJSON structures according to RFC 7946 specification.

RFC 7946: https://datatracker.ietf.org/doc/html/rfc7946
"""

from datetime import datetime
from typing import Any, Union
from uuid import UUID

from src.models.event import Event
from src.services.copernicus_service import CopernicusEvent
from src.services.gdacs_service import GDACSEvent

# Type alias for supported event types
EventType = Union[Event, GDACSEvent, CopernicusEvent]

# Valid GeoJSON geometry types per RFC 7946
VALID_GEOMETRY_TYPES = {
    "Point",
    "MultiPoint",
    "LineString",
    "MultiLineString",
    "Polygon",
    "MultiPolygon",
    "GeometryCollection",
}

# Valid GeoJSON object types
VALID_GEOJSON_TYPES = VALID_GEOMETRY_TYPES | {"Feature", "FeatureCollection"}

# WGS84 coordinate bounds (EPSG:4326)
WGS84_LNG_MIN = -180.0
WGS84_LNG_MAX = 180.0
WGS84_LAT_MIN = -90.0
WGS84_LAT_MAX = 90.0


def validate_coordinates(lng: float, lat: float) -> bool:
    """
    Validate that coordinates are within valid WGS84 (EPSG:4326) bounds.

    Per RFC 7946 Section 5, coordinates use the WGS84 datum:
    - Longitude: -180 to 180 degrees
    - Latitude: -90 to 90 degrees

    Args:
        lng: Longitude value
        lat: Latitude value

    Returns:
        True if coordinates are valid, False otherwise
    """
    try:
        lng_float = float(lng)
        lat_float = float(lat)
    except (TypeError, ValueError):
        return False

    return (
        WGS84_LNG_MIN <= lng_float <= WGS84_LNG_MAX
        and WGS84_LAT_MIN <= lat_float <= WGS84_LAT_MAX
    )


def _validate_position(position: Any) -> list[str]:
    """
    Validate a GeoJSON position (coordinate array).

    A position is an array of numbers with at least 2 elements [lng, lat]
    and optionally a third element for altitude.

    Args:
        position: The position array to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors: list[str] = []

    if not isinstance(position, (list, tuple)):
        errors.append(f"Position must be an array, got {type(position).__name__}")
        return errors

    if len(position) < 2:
        errors.append(f"Position must have at least 2 elements, got {len(position)}")
        return errors

    if len(position) > 3:
        errors.append(f"Position should have 2-3 elements, got {len(position)}")

    for i, coord in enumerate(position[:3]):
        if not isinstance(coord, (int, float)):
            errors.append(f"Position element {i} must be a number, got {type(coord).__name__}")

    if len(position) >= 2 and all(isinstance(c, (int, float)) for c in position[:2]):
        lng, lat = position[0], position[1]
        if not validate_coordinates(lng, lat):
            errors.append(
                f"Coordinates out of bounds: lng={lng}, lat={lat} "
                f"(valid: lng {WGS84_LNG_MIN} to {WGS84_LNG_MAX}, lat {WGS84_LAT_MIN} to {WGS84_LAT_MAX})"
            )

    return errors


def _validate_coordinates_array(
    coords: Any, geometry_type: str, depth: int = 0
) -> list[str]:
    """
    Recursively validate coordinates array based on geometry type.

    Args:
        coords: The coordinates to validate
        geometry_type: The GeoJSON geometry type
        depth: Current recursion depth for nested arrays

    Returns:
        List of validation error messages (empty if valid)
    """
    errors: list[str] = []

    if geometry_type == "Point":
        errors.extend(_validate_position(coords))

    elif geometry_type == "MultiPoint" or geometry_type == "LineString":
        if not isinstance(coords, (list, tuple)):
            errors.append(f"{geometry_type} coordinates must be an array")
            return errors
        if geometry_type == "LineString" and len(coords) < 2:
            errors.append("LineString must have at least 2 positions")
        for i, pos in enumerate(coords):
            pos_errors = _validate_position(pos)
            for err in pos_errors:
                errors.append(f"Position {i}: {err}")

    elif geometry_type == "MultiLineString" or geometry_type == "Polygon":
        if not isinstance(coords, (list, tuple)):
            errors.append(f"{geometry_type} coordinates must be an array")
            return errors
        for i, ring in enumerate(coords):
            if not isinstance(ring, (list, tuple)):
                errors.append(f"Ring {i} must be an array")
                continue
            if geometry_type == "Polygon":
                if len(ring) < 4:
                    errors.append(f"Polygon ring {i} must have at least 4 positions")
                elif ring[0] != ring[-1]:
                    errors.append(f"Polygon ring {i} must be closed (first == last)")
            for j, pos in enumerate(ring):
                pos_errors = _validate_position(pos)
                for err in pos_errors:
                    errors.append(f"Ring {i}, Position {j}: {err}")

    elif geometry_type == "MultiPolygon":
        if not isinstance(coords, (list, tuple)):
            errors.append("MultiPolygon coordinates must be an array")
            return errors
        for i, polygon in enumerate(coords):
            poly_errors = _validate_coordinates_array(polygon, "Polygon", depth + 1)
            for err in poly_errors:
                errors.append(f"Polygon {i}: {err}")

    return errors


def _validate_geometry(geometry: Any) -> list[str]:
    """
    Validate a GeoJSON geometry object.

    Args:
        geometry: The geometry object to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors: list[str] = []

    if geometry is None:
        return errors  # null geometry is valid per RFC 7946

    if not isinstance(geometry, dict):
        errors.append(f"Geometry must be an object, got {type(geometry).__name__}")
        return errors

    if "type" not in geometry:
        errors.append("Geometry missing required 'type' member")
        return errors

    geom_type = geometry.get("type")
    if geom_type not in VALID_GEOMETRY_TYPES:
        errors.append(f"Invalid geometry type: {geom_type}")
        return errors

    if geom_type == "GeometryCollection":
        if "geometries" not in geometry:
            errors.append("GeometryCollection missing 'geometries' member")
        elif not isinstance(geometry["geometries"], (list, tuple)):
            errors.append("GeometryCollection 'geometries' must be an array")
        else:
            for i, geom in enumerate(geometry["geometries"]):
                geom_errors = _validate_geometry(geom)
                for err in geom_errors:
                    errors.append(f"Geometry {i}: {err}")
    else:
        if "coordinates" not in geometry:
            errors.append(f"{geom_type} missing required 'coordinates' member")
        else:
            coord_errors = _validate_coordinates_array(
                geometry["coordinates"], geom_type
            )
            errors.extend(coord_errors)

    return errors


def _validate_feature(feature: Any) -> list[str]:
    """
    Validate a GeoJSON Feature object.

    Args:
        feature: The feature object to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors: list[str] = []

    if not isinstance(feature, dict):
        errors.append(f"Feature must be an object, got {type(feature).__name__}")
        return errors

    if feature.get("type") != "Feature":
        errors.append(f"Feature 'type' must be 'Feature', got '{feature.get('type')}'")

    if "geometry" not in feature:
        errors.append("Feature missing required 'geometry' member")
    else:
        geom_errors = _validate_geometry(feature["geometry"])
        errors.extend(geom_errors)

    if "properties" not in feature:
        errors.append("Feature missing required 'properties' member")
    elif feature["properties"] is not None and not isinstance(feature["properties"], dict):
        errors.append("Feature 'properties' must be an object or null")

    # Validate optional bbox
    if "bbox" in feature:
        bbox_errors = _validate_bbox(feature["bbox"])
        errors.extend(bbox_errors)

    return errors


def _validate_bbox(bbox: Any) -> list[str]:
    """
    Validate a GeoJSON bounding box.

    Per RFC 7946 Section 5, bbox is an array of 4 or 6 numbers:
    - 2D: [min_lng, min_lat, max_lng, max_lat]
    - 3D: [min_lng, min_lat, min_alt, max_lng, max_lat, max_alt]

    Args:
        bbox: The bounding box to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors: list[str] = []

    if not isinstance(bbox, (list, tuple)):
        errors.append(f"Bounding box must be an array, got {type(bbox).__name__}")
        return errors

    if len(bbox) not in (4, 6):
        errors.append(f"Bounding box must have 4 or 6 elements, got {len(bbox)}")
        return errors

    for i, val in enumerate(bbox):
        if not isinstance(val, (int, float)):
            errors.append(f"Bounding box element {i} must be a number")

    if len(bbox) >= 4 and all(isinstance(v, (int, float)) for v in bbox[:4]):
        min_lng, min_lat, max_lng, max_lat = bbox[0], bbox[1], bbox[2], bbox[3]

        if not validate_coordinates(min_lng, min_lat):
            errors.append(f"Bounding box min coordinates out of bounds: [{min_lng}, {min_lat}]")
        if not validate_coordinates(max_lng, max_lat):
            errors.append(f"Bounding box max coordinates out of bounds: [{max_lng}, {max_lat}]")

        if min_lat > max_lat:
            errors.append(f"Bounding box min_lat ({min_lat}) > max_lat ({max_lat})")

        # Note: min_lng > max_lng is valid for antimeridian-crossing bboxes

    return errors


def validate_geojson(geojson: dict) -> tuple[bool, list[str]]:
    """
    Validate a GeoJSON object according to RFC 7946 specification.

    Validates:
    - Required members (type, geometry, properties for Features)
    - Valid geometry types and coordinate structures
    - Coordinate bounds (WGS84)
    - Bounding box format if present

    Args:
        geojson: The GeoJSON object to validate

    Returns:
        Tuple of (is_valid, list of error messages)

    Example:
        >>> geojson = {"type": "Point", "coordinates": [0, 0]}
        >>> is_valid, errors = validate_geojson(geojson)
        >>> print(is_valid)  # True
    """
    errors: list[str] = []

    if not isinstance(geojson, dict):
        return False, [f"GeoJSON must be an object, got {type(geojson).__name__}"]

    if "type" not in geojson:
        return False, ["GeoJSON missing required 'type' member"]

    geojson_type = geojson.get("type")

    if geojson_type not in VALID_GEOJSON_TYPES:
        return False, [f"Invalid GeoJSON type: {geojson_type}"]

    # Validate based on type
    if geojson_type == "FeatureCollection":
        if "features" not in geojson:
            errors.append("FeatureCollection missing required 'features' member")
        elif not isinstance(geojson["features"], (list, tuple)):
            errors.append("FeatureCollection 'features' must be an array")
        else:
            for i, feature in enumerate(geojson["features"]):
                feature_errors = _validate_feature(feature)
                for err in feature_errors:
                    errors.append(f"Feature {i}: {err}")

    elif geojson_type == "Feature":
        errors.extend(_validate_feature(geojson))

    else:
        # Geometry types
        errors.extend(_validate_geometry(geojson))

    # Validate optional bbox at root level
    if "bbox" in geojson:
        bbox_errors = _validate_bbox(geojson["bbox"])
        errors.extend(bbox_errors)

    return len(errors) == 0, errors


def _serialize_value(value: Any) -> Any:
    """
    Serialize a value for GeoJSON properties.

    Handles UUID, datetime, and other non-JSON-serializable types.

    Args:
        value: The value to serialize

    Returns:
        JSON-serializable value
    """
    if isinstance(value, UUID):
        return str(value)
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    return value


def _get_event_coordinates(event: EventType) -> tuple[float, float]:
    """
    Extract longitude and latitude from an event object.

    Args:
        event: Event object (Event, GDACSEvent, or CopernicusEvent)

    Returns:
        Tuple of (longitude, latitude)

    Raises:
        ValueError: If coordinates are missing or invalid
    """
    if isinstance(event, Event):
        lng = event.longitude
        lat = event.latitude
    elif isinstance(event, (GDACSEvent, CopernicusEvent)):
        lng = event.lng
        lat = event.lat
    else:
        raise ValueError(f"Unsupported event type: {type(event).__name__}")

    if lng is None or lat is None:
        raise ValueError("Event missing coordinates")

    return float(lng), float(lat)


def _get_event_properties(event: EventType) -> dict[str, Any]:
    """
    Extract properties from an event object for GeoJSON Feature.

    Args:
        event: Event object (Event, GDACSEvent, or CopernicusEvent)

    Returns:
        Dictionary of properties
    """
    if isinstance(event, Event):
        properties = {
            "id": event.id,
            "type": event.type.value if event.type else None,
            "title": event.title,
            "description": event.description,
            "severity": event.severity.value if event.severity else None,
            "country_code": event.country_code,
            "region": event.region,
            "affected_population": event.affected_population,
            "start_date": event.start_date,
            "end_date": event.end_date,
            "is_active": event.is_active,
            "source_id": event.source_id,
            "source_url": event.source_url,
            "created_at": event.created_at,
            "updated_at": event.updated_at,
        }
    elif isinstance(event, GDACSEvent):
        properties = {
            "external_id": event.external_id,
            "type": event.event_type,
            "title": event.title,
            "description": event.description,
            "severity": event.severity,
            "country": event.country,
            "affected_population": event.population,
            "start_date": event.start_date,
            "source": "GDACS",
            "source_url": event.url,
        }
    elif isinstance(event, CopernicusEvent):
        properties = {
            "external_id": event.external_id,
            "type": event.event_type,
            "title": event.title,
            "description": event.description,
            "severity": event.severity,
            "country": event.country,
            "n_aois": event.n_aois,
            "n_products": event.n_products,
            "start_date": event.start_date,
            "source": "Copernicus",
            "source_url": event.url,
        }
    else:
        raise ValueError(f"Unsupported event type: {type(event).__name__}")

    # Serialize non-JSON-serializable values
    return {k: _serialize_value(v) for k, v in properties.items() if v is not None}


def event_to_geojson_feature(event: EventType) -> dict[str, Any]:
    """
    Convert an event to a GeoJSON Feature.

    Supports Event (database model), GDACSEvent, and CopernicusEvent types.
    The resulting Feature follows RFC 7946 specification with:
    - Point geometry at the event's location
    - Properties containing event metadata

    Args:
        event: Event object to convert

    Returns:
        GeoJSON Feature dictionary

    Raises:
        ValueError: If event has invalid or missing coordinates

    Example:
        >>> from src.services.gdacs_service import GDACSEvent
        >>> event = GDACSEvent(
        ...     external_id="EQ123",
        ...     event_type="earthquake",
        ...     title="Earthquake in Japan",
        ...     description="...",
        ...     lat=35.6762,
        ...     lng=139.6503,
        ...     country="Japan",
        ...     severity="high",
        ...     population=1000000,
        ...     start_date=datetime.now(),
        ...     url="https://...",
        ...     raw_data={}
        ... )
        >>> feature = event_to_geojson_feature(event)
        >>> print(feature["type"])  # "Feature"
    """
    lng, lat = _get_event_coordinates(event)

    if not validate_coordinates(lng, lat):
        raise ValueError(
            f"Invalid coordinates: lng={lng}, lat={lat}. "
            f"Must be within WGS84 bounds (lng: {WGS84_LNG_MIN} to {WGS84_LNG_MAX}, "
            f"lat: {WGS84_LAT_MIN} to {WGS84_LAT_MAX})"
        )

    properties = _get_event_properties(event)

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [lng, lat],
        },
        "properties": properties,
    }


def calculate_bbox(features: list[dict[str, Any]]) -> list[float] | None:
    """
    Calculate the bounding box for a list of GeoJSON Features.

    Returns the minimum bounding rectangle that contains all Point geometries
    in the format: [min_lng, min_lat, max_lng, max_lat]

    Args:
        features: List of GeoJSON Feature dictionaries

    Returns:
        Bounding box as [min_lng, min_lat, max_lng, max_lat], or None if no valid coordinates

    Example:
        >>> features = [
        ...     {"type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0]}, "properties": {}},
        ...     {"type": "Feature", "geometry": {"type": "Point", "coordinates": [10, 20]}, "properties": {}},
        ... ]
        >>> bbox = calculate_bbox(features)
        >>> print(bbox)  # [0, 0, 10, 20]
    """
    if not features:
        return None

    min_lng: float | None = None
    min_lat: float | None = None
    max_lng: float | None = None
    max_lat: float | None = None

    def update_bounds(coords: list[Any] | tuple[Any, ...]) -> None:
        """Recursively extract coordinates and update bounds."""
        nonlocal min_lng, min_lat, max_lng, max_lat

        if not coords:
            return

        # Check if this is a position array (numbers)
        if isinstance(coords[0], (int, float)):
            if len(coords) >= 2:
                lng, lat = float(coords[0]), float(coords[1])
                if validate_coordinates(lng, lat):
                    if min_lng is None or lng < min_lng:
                        min_lng = lng
                    if max_lng is None or lng > max_lng:
                        max_lng = lng
                    if min_lat is None or lat < min_lat:
                        min_lat = lat
                    if max_lat is None or lat > max_lat:
                        max_lat = lat
        else:
            # Nested array - recurse
            for item in coords:
                if isinstance(item, (list, tuple)):
                    update_bounds(item)

    for feature in features:
        if not isinstance(feature, dict):
            continue

        geometry = feature.get("geometry")
        if not geometry or not isinstance(geometry, dict):
            continue

        geom_type = geometry.get("type")
        coords = geometry.get("coordinates")

        if geom_type == "GeometryCollection":
            # Handle GeometryCollection
            geometries = geometry.get("geometries", [])
            for geom in geometries:
                if isinstance(geom, dict) and "coordinates" in geom:
                    update_bounds(geom["coordinates"])
        elif coords and isinstance(coords, list):
            update_bounds(coords)

    if min_lng is None or min_lat is None or max_lng is None or max_lat is None:
        return None

    return [min_lng, min_lat, max_lng, max_lat]


def events_to_feature_collection(
    events: list[EventType],
    include_bbox: bool = True,
) -> dict[str, Any]:
    """
    Convert a list of events to a GeoJSON FeatureCollection.

    Creates a valid RFC 7946 FeatureCollection with:
    - All events converted to Point Features
    - Optional bounding box encompassing all features
    - Invalid events are skipped with a warning

    Args:
        events: List of event objects (Event, GDACSEvent, or CopernicusEvent)
        include_bbox: Whether to calculate and include the bounding box

    Returns:
        GeoJSON FeatureCollection dictionary

    Example:
        >>> events = [gdacs_event1, gdacs_event2, copernicus_event1]
        >>> collection = events_to_feature_collection(events)
        >>> print(collection["type"])  # "FeatureCollection"
        >>> print(len(collection["features"]))  # 3
    """
    features: list[dict[str, Any]] = []

    for event in events:
        try:
            feature = event_to_geojson_feature(event)
            features.append(feature)
        except ValueError:
            # Skip events with invalid coordinates
            continue

    result: dict[str, Any] = {
        "type": "FeatureCollection",
        "features": features,
    }

    if include_bbox and features:
        bbox = calculate_bbox(features)
        if bbox:
            result["bbox"] = bbox

    return result
