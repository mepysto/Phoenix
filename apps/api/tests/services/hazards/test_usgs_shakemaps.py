"""ShakeMap aggregation against a mocked USGS API."""

import httpx
import pytest

from src.core.exceptions import ExternalAPIError
from src.services.hazards.usgs_shakemaps import FEED_URL, USGSShakeMapService


def quake(event_id: str, mmi: float, types: str = ",shakemap,") -> dict:
    return {
        "id": event_id,
        "properties": {
            "mag": 6.0, "place": f"near {event_id}", "mmi": mmi, "alert": "green", "time": 1,
            "types": types, "detail": f"https://usgs.test/detail/{event_id}.geojson",
        },
    }


def contour(value: float) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "MultiLineString", "coordinates": [[[120.123456, -8.654321], [121.0, -8.0]]]},
        "properties": {"value": value, "color": "#ffff00"},
    }


def transport(broken: set[str] = frozenset(), down: bool = False) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if down:
            return httpx.Response(503)
        if url == FEED_URL:
            return httpx.Response(200, json={"features": [
                quake("weak", 3.0), quake("strong", 6.7), quake("none", 7.0, types=",origin,"),
                quake("broken", 5.0),
            ]})
        if "/detail/" in url:
            event_id = url.rsplit("/", 1)[-1].removesuffix(".geojson")
            if event_id in broken:
                return httpx.Response(500)
            return httpx.Response(200, json={"properties": {"products": {"shakemap": [{"contents": {
                "download/cont_mmi.json": {"url": f"https://usgs.test/cont/{event_id}.json"}}}]}}})
        return httpx.Response(200, json={"features": [contour(3.5), contour(4.0), contour(6.0)]})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_only_shakemap_events_strongest_first_and_weak_contours_dropped() -> None:
    fc = await USGSShakeMapService(httpx.AsyncClient(transport=transport())).get_shakemaps()
    events = [f["properties"]["event_id"] for f in fc["features"]]
    assert "none" not in events  # no ShakeMap product
    assert events[0] == "strong"  # sorted by felt intensity
    assert {f["properties"]["mmi"] for f in fc["features"]} == {4.0, 6.0}  # MMI < 4 dropped
    assert fc["features"][0]["geometry"]["coordinates"][0][0] == [120.1235, -8.6543]


@pytest.mark.asyncio
async def test_one_broken_shakemap_does_not_hide_the_others() -> None:
    service = USGSShakeMapService(httpx.AsyncClient(transport=transport(broken={"broken"})))
    fc = await service.get_shakemaps()
    events = {f["properties"]["event_id"] for f in fc["features"]}
    assert events == {"strong", "weak"}


@pytest.mark.asyncio
async def test_usgs_down_without_cache_is_an_upstream_error() -> None:
    service = USGSShakeMapService(httpx.AsyncClient(transport=transport(down=True)))
    with pytest.raises(ExternalAPIError):
        await service.get_shakemaps()


@pytest.mark.asyncio
async def test_usgs_down_with_cache_serves_stale() -> None:
    service = USGSShakeMapService(httpx.AsyncClient(transport=transport()))
    fresh = await service.get_shakemaps()
    service._client = httpx.AsyncClient(transport=transport(down=True))
    service.results.ttl_seconds = 0
    stale = await service.get_shakemaps()
    assert stale["stale"] is True and stale["features"] == fresh["features"]
