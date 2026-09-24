"""Local radio stations near a place, from the Radio Browser directory (G-18).

Why: emergency broadcasts and local-language news from the affected area,
and a station that has gone off air is itself a sign of power or
communications loss. The directory API is free for any software; it asks
for an identifying User-Agent. Streams are played by the browser directly
(audio is not proxied); only https streams are offered for in-page play.
"""

import math
from collections import OrderedDict
from typing import Any

import httpx

from src.services.hazards.cache import StaleOnErrorCache

SERVERS = ("de1", "de2", "fi1")  # tried in order
SEARCH_URL = "https://{server}.api.radio-browser.info/json/stations/search"
USER_AGENT = "Phoenix-disaster-map/0.1 (+https://github.com/mepysto/Phoenix)"
CACHE_TTL_SECONDS = 3600
RETRY_AFTER_ERROR_SECONDS = 300
MAX_CELLS = 256
REQUEST_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


def station(raw: dict[str, Any], lat: float, lng: float) -> dict[str, Any] | None:
    """Normalise one directory entry; entries without a usable position are dropped."""
    s_lat, s_lng = raw.get("geo_lat"), raw.get("geo_long")
    if not isinstance(s_lat, int | float) or not isinstance(s_lng, int | float):
        return None
    url = str(raw.get("url_resolved") or raw.get("url") or "")
    homepage = str(raw.get("homepage") or "")
    return {
        "id": str(raw.get("stationuuid") or ""),
        "name": str(raw.get("name") or "").strip()[:100] or "Radio",
        # Browsers block http audio on https pages: only https streams play in-page
        "stream_url": url if url.startswith("https://") else None,
        "listen_url": url if url.startswith(("https://", "http://")) else None,
        "homepage": homepage if homepage.startswith(("https://", "http://")) else None,
        "codec": str(raw.get("codec") or "")[:10] or None,
        "bitrate": raw.get("bitrate") if isinstance(raw.get("bitrate"), int) and raw["bitrate"] > 0 else None,
        "country_code": str(raw.get("countrycode") or "")[:2] or None,
        "language": str(raw.get("language") or "")[:40] or None,
        "latitude": float(s_lat),
        "longitude": float(s_lng),
        "distance_km": round(_distance_km(lat, lng, float(s_lat), float(s_lng)), 1),
        # Directory's own health check: 0 means the stream failed its last check
        "on_air": raw.get("lastcheckok") == 1,
        "last_checked": raw.get("lastchecktime_iso8601") or None,
    }


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 2 * 6371 * math.asin(min(1.0, math.sqrt(h)))


class RadioService:
    def __init__(self) -> None:
        self._cells: OrderedDict[tuple[float, float, int], StaleOnErrorCache] = OrderedDict()

    async def nearby(self, lat: float, lng: float, radius_km: float, limit: int) -> list[dict[str, Any]]:
        # ~10 km cells and 25 km radius steps: nearby viewers share one directory call
        cell = (round(lat, 1), round(lng, 1), int(-(-radius_km // 25) * 25))
        cache = self._cells.get(cell)
        if cache is None:
            cache = StaleOnErrorCache("Radio Browser", CACHE_TTL_SECONDS, RETRY_AFTER_ERROR_SECONDS)
            self._cells[cell] = cache
            if len(self._cells) > MAX_CELLS:
                self._cells.popitem(last=False)

        async def fetch() -> dict[str, Any]:
            c_lat, c_lng, radius = cell
            params = {
                "geo_lat": c_lat,
                "geo_long": c_lng,
                "geo_distance": radius * 1000,
                "has_geo_info": "true",
                "order": "clickcount",
                "reverse": "true",
                "limit": 100,
            }
            last_error: Exception | None = None
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
                for server in SERVERS:
                    try:
                        response = await client.get(SEARCH_URL.format(server=server), params=params)
                        response.raise_for_status()
                        return {"stations": response.json()}
                    except (httpx.HTTPError, ValueError) as e:
                        last_error = e
            raise last_error or ValueError("no Radio Browser server answered")

        raw = (await cache.get(fetch))["stations"]
        stations = [s for s in (station(r, lat, lng) for r in raw if isinstance(r, dict)) if s]
        stations = [s for s in stations if s["distance_km"] <= radius_km and s["id"]]
        # The directory already ranks by popularity (click count)
        return stations[:limit]


radio_service = RadioService()
