"""Active tropical cyclones from the U.S. National Hurricane Center.

Source: NOAA NWS NHC tropical MapServer (U.S. Government public domain).
Covers the Atlantic, East Pacific and Central Pacific basins. Each basin has
five storm "slots" (AT1..AT5, EP1..EP5, CP1..CP5), each with its own layers,
so a request fans out to the active slots and merges the result.
"""

import asyncio
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from src.core.exceptions import ExternalAPIError

logger = logging.getLogger(__name__)

MAPSERVER = (
    "https://mapservices.weather.noaa.gov/tropical/rest/services/tropical/"
    "NHC_tropical_weather/MapServer"
)
CACHE_TTL_SECONDS = 600  # NHC advisories are issued every 3-6 hours
LAYER_IDS_TTL_SECONDS = 24 * 3600
REQUEST_TIMEOUT = httpx.Timeout(20.0, connect=10.0)

# MapServer layer name suffix -> feature kind on the map
LAYER_KINDS = {
    "Forecast Points": "position",
    "Forecast Track": "track",
    "Forecast Cone": "cone",
    "Past Track": "past_track",
}
SLOT_LAYER = re.compile(r"^(?P<slot>(AT|EP|CP)[1-5]) (?P<suffix>.+)$")


@dataclass
class _Cache:
    layer_ids: dict[str, dict[str, int]] = field(default_factory=dict)  # slot -> kind -> id
    layer_ids_at: float = 0.0
    collection: dict[str, Any] | None = None
    collection_at: float = 0.0


def _round_coords(value: Any, digits: int = 5) -> Any:
    """Round nested GeoJSON coordinates (~1 m) to shrink the payload."""
    if isinstance(value, float):
        return round(value, digits)
    if isinstance(value, list):
        return [_round_coords(v, digits) for v in value]
    return value


def _normalise(kind: str, slot: str, props: dict[str, Any]) -> dict[str, Any]:
    """Keep a small, stable property set (MapServer field names vary by layer)."""
    name = str(props.get("stormname") or "").strip()
    wind = props.get("maxwind")
    return {
        "kind": kind,
        "slot": slot,
        "storm_name": re.sub(r"^(Hurricane|Tropical Storm|Tropical Depression)\s+", "", name),
        "storm_type": props.get("stormtype"),
        "basin": props.get("basin"),
        "advisory": str(props.get("advisnum") or "") or None,
        "advisory_date": props.get("advdate"),
        # Forecast position fields (absent on lines/polygons)
        "max_wind_kt": int(wind) if isinstance(wind, int | float) else None,
        "saffir_simpson": props.get("ssnum"),
        "pressure_mb": props.get("mslp"),
        "valid_time": props.get("validtime") or props.get("fldatelbl"),
        "tau_hours": props.get("tau"),
    }


class NHCCycloneService:
    """Fetch and cache active NHC cyclones as one GeoJSON FeatureCollection."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._cache = _Cache()
        self._lock = asyncio.Lock()

    async def get_cyclones(self) -> dict[str, Any]:
        """Current cyclones; serves stale data (flagged) if NOAA is down."""
        async with self._lock:
            now = time.monotonic()
            if self._cache.collection and now - self._cache.collection_at < CACHE_TTL_SECONDS:
                return self._cache.collection
            try:
                collection = await self._fetch()
            except (httpx.HTTPError, ValueError, KeyError) as e:
                if self._cache.collection:
                    logger.warning("NHC unavailable, serving cached cyclones: %r", e)
                    return {**self._cache.collection, "stale": True}
                raise ExternalAPIError("NHC tropical service unavailable", service_name="NHC") from e
            self._cache.collection, self._cache.collection_at = collection, now
            return collection

    async def _fetch(self) -> dict[str, Any]:
        async with self._http() as client:
            layer_ids = await self._layer_ids(client)
            positions = {slot: kinds["position"] for slot, kinds in layer_ids.items() if "position" in kinds}
            # 1) which slots currently hold a storm?
            counts = await asyncio.gather(
                *(self._query(client, layer_id, count_only=True) for layer_id in positions.values())
            )
            active = [slot for slot, count in zip(positions, counts, strict=True) if count]
            # 2) all layers of the active slots
            jobs = [
                (slot, kind, layer_id)
                for slot in active
                for kind, layer_id in layer_ids[slot].items()
            ]
            results = await asyncio.gather(*(self._query(client, lid) for _, _, lid in jobs))

        features = [
            {
                "type": "Feature",
                "geometry": {
                    "type": feature["geometry"]["type"],
                    "coordinates": _round_coords(feature["geometry"]["coordinates"]),
                },
                "properties": _normalise(kind, slot, feature.get("properties") or {}),
            }
            for (slot, kind, _), collection in zip(jobs, results, strict=True)
            for feature in collection.get("features", [])
            if feature.get("geometry")
        ]
        return {
            "type": "FeatureCollection",
            "features": features,
            "source": "NOAA National Hurricane Center",
            "active_storms": len(active),
            "stale": False,
        }

    async def _layer_ids(self, client: httpx.AsyncClient) -> dict[str, dict[str, int]]:
        """Slot -> kind -> layer id, discovered by name (NOAA renumbers layers)."""
        now = time.monotonic()
        if self._cache.layer_ids and now - self._cache.layer_ids_at < LAYER_IDS_TTL_SECONDS:
            return self._cache.layer_ids
        response = await client.get(MAPSERVER, params={"f": "json"})
        response.raise_for_status()
        ids: dict[str, dict[str, int]] = {}
        for layer in response.json()["layers"]:
            match = SLOT_LAYER.match(layer["name"])
            if match and match["suffix"] in LAYER_KINDS:
                ids.setdefault(match["slot"], {})[LAYER_KINDS[match["suffix"]]] = layer["id"]
        if not ids:
            raise ValueError("NHC MapServer layout changed: no storm slot layers found")
        self._cache.layer_ids, self._cache.layer_ids_at = ids, now
        return ids

    async def _query(self, client: httpx.AsyncClient, layer_id: int, count_only: bool = False) -> Any:
        params = {"where": "1=1", "outFields": "*", "f": "json" if count_only else "geojson"}
        if count_only:
            params["returnCountOnly"] = "true"
        response = await client.get(f"{MAPSERVER}/{layer_id}/query", params=params)
        response.raise_for_status()
        body = response.json()
        return body.get("count", 0) if count_only else body

    def _http(self) -> httpx.AsyncClient:
        if self._client is not None:
            # Injected client (tests): don't close it here
            return _Borrowed(self._client)  # type: ignore[return-value]
        return httpx.AsyncClient(timeout=REQUEST_TIMEOUT, headers={"User-Agent": "Phoenix/0.1"})


class _Borrowed:
    """Async context manager that yields a client without closing it."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def __aenter__(self) -> httpx.AsyncClient:
        return self._client

    async def __aexit__(self, *exc: object) -> None:
        return None


nhc_cyclone_service = NHCCycloneService()
