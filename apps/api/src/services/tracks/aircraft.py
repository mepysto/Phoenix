"""Aircraft around a place from ADS-B (adsb.lol, ODbL) (G-11).

Used to see relief, firefighting and medevac flights and airspace activity
over an affected area. Requests are proxied (no browser → adsb.lol traffic)
and cached per ~50 km cell for a few seconds so many viewers cost one call.

Privacy: aircraft whose operators enrolled in the FAA privacy programmes
(PIA, LADD) are dropped. Phoenix does not track individuals.
"""

from collections import OrderedDict
from typing import Any

import httpx

from src.services.hazards.cache import StaleOnErrorCache

API_URL = "https://api.adsb.lol/v2/point/{lat}/{lng}/{radius}"
MAX_RADIUS_NM = 250  # adsb.lol limit
CACHE_TTL_SECONDS = 10
RETRY_AFTER_ERROR_SECONDS = 30
MAX_CELLS = 128
REQUEST_TIMEOUT = httpx.Timeout(15.0, connect=5.0)
# adsb.lol rejects generic client user agents; identify the project instead
USER_AGENT = "Phoenix-disaster-map/0.1 (+https://github.com/mepysto/Phoenix)"

# readsb database flags (checked against /v2/mil, /v2/pia and /v2/ladd)
FLAG_MILITARY = 1
FLAG_PIA = 4
FLAG_LADD = 8
PRIVATE = FLAG_PIA | FLAG_LADD


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def to_geojson(payload: dict[str, Any]) -> dict[str, Any]:
    """adsb.lol response → GeoJSON points; private and position-less aircraft are dropped."""
    features = []
    for ac in payload.get("ac") or []:
        flags = ac.get("dbFlags") or 0
        lat, lng = _number(ac.get("lat")), _number(ac.get("lon"))
        if flags & PRIVATE or lat is None or lng is None:
            continue
        altitude = ac.get("alt_baro")
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [round(lng, 5), round(lat, 5)]},
                "properties": {
                    "hex": str(ac.get("hex", ""))[:8],
                    "callsign": str(ac.get("flight") or "").strip()[:10] or None,
                    "type": str(ac.get("t") or "")[:6] or None,
                    "altitude_ft": _number(altitude),
                    "on_ground": altitude == "ground",
                    "speed_kt": _number(ac.get("gs")),
                    "track_deg": _number(ac.get("track")),
                    "military": bool(flags & FLAG_MILITARY),
                    "seen_s": _number(ac.get("seen")),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


class AircraftService:
    def __init__(self) -> None:
        self._cells: OrderedDict[tuple[float, float, int], StaleOnErrorCache] = OrderedDict()

    @staticmethod
    def cell(lat: float, lng: float, radius_nm: float) -> tuple[float, float, int]:
        """Snap to a 0.5° grid and 25 NM radius steps so nearby viewers share one request."""
        radius = min(MAX_RADIUS_NM, max(25, int(-(-radius_nm // 25) * 25)))
        return round(lat * 2) / 2, round(lng * 2) / 2, radius

    async def around(self, lat: float, lng: float, radius_nm: float) -> dict[str, Any]:
        key = self.cell(lat, lng, radius_nm)
        cache = self._cells.get(key)
        if cache is None:
            cache = StaleOnErrorCache(
                "adsb.lol", CACHE_TTL_SECONDS, retry_after_error_seconds=RETRY_AFTER_ERROR_SECONDS
            )
            self._cells[key] = cache
            if len(self._cells) > MAX_CELLS:
                self._cells.popitem(last=False)
        else:
            self._cells.move_to_end(key)

        async def fetch() -> dict[str, Any]:
            cell_lat, cell_lng, radius = key
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers={"User-Agent": USER_AGENT}) as client:
                response = await client.get(API_URL.format(lat=cell_lat, lng=cell_lng, radius=radius))
                response.raise_for_status()
                return to_geojson(response.json())

        return await cache.get(fetch)


aircraft_service = AircraftService()
