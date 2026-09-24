"""NHC cyclone aggregation against a mocked NOAA MapServer."""

import httpx
import pytest

from src.core.exceptions import ExternalAPIError
from src.services.hazards.nhc_cyclones import NHCCycloneService

LAYERS = [
    {"id": 10, "name": "EP1 Forecast Points"},
    {"id": 11, "name": "EP1 Forecast Track"},
    {"id": 12, "name": "EP1 Forecast Cone"},
    {"id": 13, "name": "EP1 Past Track"},
    {"id": 14, "name": "EP1 Watch-Warning"},  # ignored kind
    {"id": 20, "name": "AT1 Forecast Points"},  # empty slot
    {"id": 21, "name": "AT1 Forecast Cone"},
    {"id": 99, "name": "Graphical Tropical Weather Outlook"},  # not a slot
]
POLO = {
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [-102.40000000029966, 15.999999999600448]},
    "properties": {
        "stormname": "Hurricane Polo", "stormtype": "MH", "basin": "EP", "advisnum": "14",
        "maxwind": 140, "ssnum": 5, "mslp": 923, "tau": 0,
    },
}


def make_transport(calls: list[str], fail: bool = False) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path + ("?count" if "returnCountOnly" in str(request.url) else ""))
        if fail:
            return httpx.Response(503)
        path = request.url.path
        if path.endswith("/MapServer"):
            return httpx.Response(200, json={"layers": LAYERS})
        layer = int(path.split("/")[-2])
        if "returnCountOnly" in str(request.url):
            return httpx.Response(200, json={"count": 9 if layer == 10 else 0})
        features = [POLO] if layer == 10 else [{**POLO, "geometry": {"type": "LineString", "coordinates": [[0.0, 0.0], [1.0, 1.0]]}}]
        return httpx.Response(200, json={"type": "FeatureCollection", "features": features})

    return httpx.MockTransport(handler)


@pytest.fixture
def calls() -> list[str]:
    return []


@pytest.mark.asyncio
async def test_queries_only_active_slots_and_normalises(calls) -> None:
    service = NHCCycloneService(httpx.AsyncClient(transport=make_transport(calls)))
    fc = await service.get_cyclones()

    assert fc["active_storms"] == 1
    kinds = sorted(f["properties"]["kind"] for f in fc["features"])
    assert kinds == ["cone", "past_track", "position", "track"]
    # Empty AT1 slot was only counted, never fetched; Watch-Warning ignored
    fetched = [c for c in calls if c.endswith("/query")]
    assert all("/20/" not in c and "/21/" not in c and "/14/" not in c for c in fetched)

    position = next(f for f in fc["features"] if f["properties"]["kind"] == "position")
    assert position["properties"]["storm_name"] == "Polo"  # prefix stripped
    assert position["properties"]["max_wind_kt"] == 140
    assert position["properties"]["saffir_simpson"] == 5
    assert position["geometry"]["coordinates"] == [-102.4, 16.0]  # rounded


@pytest.mark.asyncio
async def test_result_is_cached(calls) -> None:
    service = NHCCycloneService(httpx.AsyncClient(transport=make_transport(calls)))
    await service.get_cyclones()
    first = len(calls)
    await service.get_cyclones()
    assert len(calls) == first


@pytest.mark.asyncio
async def test_serves_stale_data_when_noaa_goes_down(calls) -> None:
    service = NHCCycloneService(httpx.AsyncClient(transport=make_transport(calls)))
    fresh = await service.get_cyclones()
    service.results.ttl_seconds = 0  # force a refresh
    service._client = httpx.AsyncClient(transport=make_transport(calls, fail=True))

    stale = await service.get_cyclones()
    assert stale["stale"] is True
    assert stale["features"] == fresh["features"]


@pytest.mark.asyncio
async def test_no_cache_and_noaa_down_raises_upstream_error(calls) -> None:
    service = NHCCycloneService(httpx.AsyncClient(transport=make_transport(calls, fail=True)))
    with pytest.raises(ExternalAPIError):
        await service.get_cyclones()
