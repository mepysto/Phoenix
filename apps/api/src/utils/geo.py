"""PostGIS geometry utilities for spatial operations."""

from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import cast, func


def make_point_expr(lat: float, lng: float) -> Any:
    """Create PostGIS POINT expression from latitude/longitude.

    Creates a PostGIS geometry using ST_SetSRID(ST_MakePoint(lng, lat), 4326)
    for WGS84 coordinate system.

    Args:
        lat: Latitude value (-90 to 90)
        lng: Longitude value (-180 to 180)

    Returns:
        SQLAlchemy expression for PostGIS POINT geometry
    """
    return func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)


def validate_lat_lng(lat: float | None, lng: float | None) -> bool:
    """Validate that latitude and longitude values are within valid bounds.

    Checks that:
    - Both values are not None
    - Latitude is between -90 and 90
    - Longitude is between -180 and 180

    Args:
        lat: Latitude value to validate
        lng: Longitude value to validate

    Returns:
        True if coordinates are valid, False otherwise
    """
    if lat is None or lng is None:
        return False
    try:
        lat_float = float(lat)
        lng_float = float(lng)
    except (TypeError, ValueError):
        return False
    return -90 <= lat_float <= 90 and -180 <= lng_float <= 180


def make_bbox_filter(
    min_lng: float,
    min_lat: float,
    max_lng: float,
    max_lat: float,
) -> Any:
    """Create PostGIS bounding box envelope for spatial queries.

    Creates a PostGIS geometry envelope using ST_MakeEnvelope
    for filtering spatial data within a bounding box.

    Args:
        min_lng: Minimum longitude (west)
        min_lat: Minimum latitude (south)
        max_lng: Maximum longitude (east)
        max_lat: Maximum latitude (north)

    Returns:
        SQLAlchemy expression for PostGIS bounding box geometry
    """
    return func.ST_MakeEnvelope(min_lng, min_lat, max_lng, max_lat, 4326)


def point_within_bbox(
    location_column: Any,
    min_lng: float,
    min_lat: float,
    max_lng: float,
    max_lat: float,
) -> Any:
    """Create PostGIS ST_Within expression for bounding box filter.

    Args:
        location_column: SQLAlchemy column containing PostGIS geometry
        min_lng: Minimum longitude (west)
        min_lat: Minimum latitude (south)
        max_lng: Maximum longitude (east)
        max_lat: Maximum latitude (north)

    Returns:
        SQLAlchemy expression for spatial containment check
    """
    bbox = make_bbox_filter(min_lng, min_lat, max_lng, max_lat)
    return func.ST_Within(location_column, bbox)


def distance_between_points(
    point1_column: Any,
    lat: float,
    lng: float,
) -> Any:
    """Calculate distance between a geometry column and a point.

    Uses ST_Distance for calculation (returns distance in degrees for geography).

    Args:
        point1_column: SQLAlchemy column containing PostGIS geometry
        lat: Latitude of reference point
        lng: Longitude of reference point

    Returns:
        SQLAlchemy expression for distance calculation
    """
    ref_point = make_point_expr(lat, lng)
    return func.ST_Distance(point1_column, ref_point)


def point_within_distance(
    location_column: Any,
    lat: float,
    lng: float,
    distance_meters: int,
) -> Any:
    """Filter points within a distance using PostGIS ST_DWithin.

    Casts geometry to geography for accurate distance calculation in meters.

    Args:
        location_column: SQLAlchemy column (PostGIS geometry)
        lat: Reference point latitude
        lng: Reference point longitude
        distance_meters: Search radius in meters

    Returns:
        SQLAlchemy expression for ST_DWithin check
    """
    ref_point = make_point_expr(lat, lng)
    return func.ST_DWithin(
        cast(location_column, Geography),
        cast(ref_point, Geography),
        distance_meters,
    )


def distance_meters(
    location_column: Any,
    lat: float,
    lng: float,
) -> Any:
    """Calculate distance between a geometry column and a point in meters.

    Uses ST_Distance with geography casting for accurate meter-based distance.

    Args:
        location_column: SQLAlchemy column containing PostGIS geometry
        lat: Latitude of reference point
        lng: Longitude of reference point

    Returns:
        SQLAlchemy expression for distance calculation in meters
    """
    ref_point = make_point_expr(lat, lng)
    return func.ST_Distance(
        cast(location_column, Geography),
        cast(ref_point, Geography),
    )
