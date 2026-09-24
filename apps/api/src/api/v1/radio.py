"""Local radio near a place (M6, G-18)."""

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel

from src.services.radio import radio_service

router = APIRouter()


class RadioStation(BaseModel):
    id: str
    name: str
    # https stream playable in the page; None for http-only stations
    stream_url: str | None
    listen_url: str | None
    homepage: str | None
    codec: str | None
    bitrate: int | None
    country_code: str | None
    language: str | None
    latitude: float
    longitude: float
    distance_km: float
    # The directory's last health check passed
    on_air: bool
    last_checked: str | None


class RadioNearbyResponse(BaseModel):
    stations: list[RadioStation]


@router.get("/nearby", response_model=RadioNearbyResponse)
async def radio_nearby(
    response: Response,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(default=100, gt=0, le=300),
    limit: int = Query(default=10, ge=1, le=30),
) -> RadioNearbyResponse:
    """Stations near a point from the Radio Browser directory, most listened first."""
    response.headers["Cache-Control"] = "public, max-age=600"
    stations = await radio_service.nearby(lat, lng, radius_km, limit)
    return RadioNearbyResponse(stations=[RadioStation(**s) for s in stations])
