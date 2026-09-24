"""Earth-observation satellites: live positions and passes over a place (G-13).

Orbits come from CelesTrak's "Earth resources" group (public GP data from
18th Space Defense Squadron), propagated with SGP4 via skyfield. CelesTrak
asks clients not to refetch unchanged data more than every ~2 hours; the
elements are cached for 6.

Why it matters for response: knowing when Sentinel, Landsat or a commercial
imager next passes over an affected area tells responders when to expect
(or request, e.g. via Copernicus EMS) fresh imagery.
"""

import asyncio
import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from skyfield.api import EarthSatellite, load, wgs84

from src.services.hazards.cache import StaleOnErrorCache

CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php"
GROUPS = ("resource",)  # Earth resources: Sentinel, Landsat, WorldView, ...
CACHE_TTL_SECONDS = 6 * 3600
# CelesTrak's policy: stop querying after an error; a human-scale pause instead
RETRY_AFTER_ERROR_SECONDS = 3600
REQUEST_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
# Elements older than this give positions off by hundreds of km: skip them
MAX_ELEMENT_AGE_DAYS = 14
PASS_CACHE_SIZE = 256

_ts = load.timescale(builtin=True)  # no network download


@dataclass(frozen=True)
class Satellite:
    name: str
    norad_id: int
    orbit: EarthSatellite


@dataclass(frozen=True)
class Pass:
    name: str
    norad_id: int
    rise: datetime
    culmination: datetime
    set: datetime
    max_elevation_deg: float
    # Sun above the horizon at the place during culmination: optical imagers
    # (Sentinel-2, Landsat) only see the ground by day; radar (Sentinel-1) any time
    daylight: bool


def solar_elevation_deg(lat: float, lng: float, when: datetime) -> float:
    """Sun's elevation above the horizon (NOAA approximation, ~0.5 degree accuracy)."""
    day_of_year = when.timetuple().tm_yday
    hour = when.hour + when.minute / 60 + when.second / 3600
    gamma = 2 * math.pi / 365 * (day_of_year - 1 + (hour - 12) / 24)
    declination = (
        0.006918 - 0.399912 * math.cos(gamma) + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma) + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma) + 0.00148 * math.sin(3 * gamma)
    )
    equation_of_time = 229.18 * (
        0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma)
    )
    solar_minutes = hour * 60 + equation_of_time + 4 * lng
    hour_angle = math.radians(solar_minutes / 4 - 180)
    phi = math.radians(lat)
    cos_zenith = math.sin(phi) * math.sin(declination) + math.cos(phi) * math.cos(declination) * math.cos(hour_angle)
    return 90 - math.degrees(math.acos(max(-1.0, min(1.0, cos_zenith))))


def parse_tle(text: str) -> list[tuple[str, str, str]]:
    """(name, line1, line2) triples from 3-line TLE text; malformed entries are skipped."""
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    triples = []
    i = 0
    while i + 2 < len(lines):
        name, line1, line2 = lines[i], lines[i + 1], lines[i + 2]
        if line1.startswith("1 ") and line2.startswith("2 ") and not name.startswith(("1 ", "2 ")):
            triples.append((name.strip(), line1, line2))
            i += 3
        else:
            i += 1  # resynchronise on the next name line
    return triples


class SatelliteService:
    def __init__(self) -> None:
        self._cache = StaleOnErrorCache(
            "CelesTrak", CACHE_TTL_SECONDS, retry_after_error_seconds=RETRY_AFTER_ERROR_SECONDS
        )
        self._parsed_for: str | None = None
        self._satellites: list[Satellite] = []
        # Pass searches cost ~0.5 s CPU: reuse them per ~10 km cell and hour
        self._passes: dict[tuple, list[Pass]] = {}

    async def _fetch(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, follow_redirects=True) as client:
            texts = []
            for group in GROUPS:
                response = await client.get(CELESTRAK_URL, params={"GROUP": group, "FORMAT": "tle"})
                response.raise_for_status()
                if not parse_tle(response.text):  # e.g. an HTML error page
                    raise ValueError("CelesTrak returned no element sets")
                texts.append(response.text)
        return {"tle": "\n".join(texts)}

    async def satellites(self, now: datetime | None = None) -> list[Satellite]:
        tle = (await self._cache.get(self._fetch))["tle"]
        if tle != self._parsed_for:
            self._satellites = self._build(tle, now or datetime.now(UTC))
            self._parsed_for = tle
        return self._satellites

    @staticmethod
    def _build(tle: str, now: datetime) -> list[Satellite]:
        seen: set[int] = set()
        result = []
        for name, line1, line2 in parse_tle(tle):
            try:
                orbit = EarthSatellite(line1, line2, name, _ts)
            except (ValueError, IndexError):
                continue
            norad = int(orbit.model.satnum)
            age = now - orbit.epoch.utc_datetime()
            if norad in seen or age > timedelta(days=MAX_ELEMENT_AGE_DAYS):
                continue
            seen.add(norad)
            result.append(Satellite(name=name, norad_id=norad, orbit=orbit))
        return result

    async def positions(self, at: datetime) -> dict[str, Any]:
        """GeoJSON points (sub-satellite points) for every satellite at `at`."""
        satellites = await self.satellites()
        return await asyncio.to_thread(positions_geojson, satellites, at)

    async def passes(
        self, lat: float, lng: float, start: datetime, hours: float, min_elevation: float
    ) -> list[Pass]:
        satellites = await self.satellites()
        start = start.replace(minute=0, second=0, microsecond=0)
        key = (round(lat, 1), round(lng, 1), start, hours, min_elevation, self._parsed_for and hash(self._parsed_for))
        if key not in self._passes:
            if len(self._passes) >= PASS_CACHE_SIZE:
                self._passes.pop(next(iter(self._passes)))  # oldest first
            self._passes[key] = await asyncio.to_thread(
                find_passes, satellites, round(lat, 1), round(lng, 1), start, hours, min_elevation
            )
        return self._passes[key]


def positions_geojson(satellites: list[Satellite], at: datetime) -> dict[str, Any]:
    t = _ts.from_datetime(at)
    features = []
    for sat in satellites:
        position = sat.orbit.at(t)
        lat, lng = wgs84.latlon_of(position)
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(float(lng.degrees), 4), round(float(lat.degrees), 4)],
                },
                "properties": {
                    "name": sat.name,
                    "norad_id": sat.norad_id,
                    "altitude_km": round(float(wgs84.height_of(position).km)),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features, "at": at.isoformat()}


def find_passes(
    satellites: list[Satellite],
    lat: float,
    lng: float,
    start: datetime,
    hours: float,
    min_elevation: float,
) -> list[Pass]:
    """Passes rising above `min_elevation` degrees as seen from (lat, lng), soonest first."""
    place = wgs84.latlon(lat, lng)
    t0, t1 = _ts.from_datetime(start), _ts.from_datetime(start + timedelta(hours=hours))
    passes = []
    for sat in satellites:
        times, kinds = sat.orbit.find_events(place, t0, t1, altitude_degrees=min_elevation)
        rise = culmination = None
        for t, kind in zip(times, kinds, strict=True):
            if kind == 0:
                rise, culmination = t, None
            elif kind == 1 and rise is not None:
                culmination = t
            elif kind == 2 and rise is not None and culmination is not None:
                elevation = (sat.orbit - place).at(culmination).altaz()[0].degrees
                peak = culmination.utc_datetime()
                passes.append(
                    Pass(
                        name=sat.name,
                        norad_id=sat.norad_id,
                        rise=rise.utc_datetime(),
                        culmination=peak,
                        set=t.utc_datetime(),
                        max_elevation_deg=round(float(elevation), 1),
                        daylight=solar_elevation_deg(lat, lng, peak) > 0,
                    )
                )
                rise = culmination = None
    return sorted(passes, key=lambda p: p.culmination)


satellite_service = SatelliteService()
