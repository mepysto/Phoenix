from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, model_validator


class Location(BaseModel):
    """Geographic location with optional coordinates and region info."""

    lat: float | None = None  # NULL 허용 (좌표 없는 이벤트)
    lng: float | None = None
    country: str | None = None
    country_code: str | None = None
    region: str | None = None


class DisplayPoint(BaseModel):
    """UI 표시용 좌표 (실제 좌표 또는 admin_area centroid)."""

    lat: float
    lng: float
    source: Literal["event", "admin_centroid", "country_centroid"]


class DataSourceRef(BaseModel):
    id: UUID
    name: str
    type: str


class GeoJSONGeometry(BaseModel):
    type: str
    coordinates: list[Any]


class EventResponse(BaseModel):
    id: UUID
    type: str
    title: str
    description: str | None = None
    location: Location
    geo_precision: str | None = None

    display_point: DisplayPoint | None = None
    severity: str
    affected_population: int | None = None
    affected_area_km2: float | None = None
    start_date: datetime
    end_date: datetime | None = None
    is_active: bool
    sources: list[DataSourceRef]
    geometry: GeoJSONGeometry | None = None
    created_at: datetime
    updated_at: datetime


class GeoLayerResponse(BaseModel):
    id: UUID
    event_id: UUID
    layer_type: str
    geometry: GeoJSONGeometry
    properties: dict[str, Any]
    timestamp: datetime | None = None


class DatasetResponse(BaseModel):
    id: UUID
    event_id: UUID
    name: str
    type: str | None = None
    url: str | None = None
    license: str | None = None
    metadata: dict[str, Any] | None = None


class EventMetricResponse(BaseModel):
    time: datetime
    event_id: UUID
    metric_type: str
    value: float


class EventDetailResponse(EventResponse):
    layers: list[GeoLayerResponse] = []
    datasets: list[DatasetResponse] = []
    metrics: list[EventMetricResponse] = []


class Pagination(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class EventListResponse(BaseModel):
    data: list[EventResponse]
    pagination: Pagination


class EventFilter(BaseModel):
    types: list[str] | None = None
    severities: list[str] | None = None
    start_date: str | None = None
    end_date: str | None = None
    min_lng: float | None = None
    min_lat: float | None = None
    max_lng: float | None = None
    max_lat: float | None = None
    center_lat: float | None = None
    center_lng: float | None = None
    radius_km: float | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_radius_params(self) -> "EventFilter":
        radius_params = [self.center_lat, self.center_lng, self.radius_km]
        provided = [p is not None for p in radius_params]
        if any(provided) and not all(provided):
            raise ValueError(
                "center_lat, center_lng, and radius_km must all be provided together"
            )
        return self
