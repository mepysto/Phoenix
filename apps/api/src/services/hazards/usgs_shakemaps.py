"""Shaking-intensity contours for recent significant earthquakes (USGS ShakeMap).

Source: USGS Earthquake Hazards Program (U.S. Government public domain).
For earthquakes in the past week that have a ShakeMap, fetch the Modified
Mercalli Intensity contours (cont_mmi.json) and merge them into one GeoJSON
FeatureCollection. Contours show where shaking was strongest, i.e. where
damage is most likely.
"""

import asyncio
from typing import Any

import httpx

from src.services.hazards.cache import StaleOnErrorCache, round_coords

FEED_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_week.geojson"
CACHE_TTL_SECONDS = 600
MAX_EVENTS = 15
# MMI III (weak) and below is noise at map scale; IV+ is broadly felt
MIN_CONTOUR_MMI = 4.0
REQUEST_TIMEOUT = httpx.Timeout(20.0, connect=10.0)


class USGSShakeMapService:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self.results = StaleOnErrorCache("USGS ShakeMap", CACHE_TTL_SECONDS)

    async def get_shakemaps(self) -> dict[str, Any]:
        return await self.results.get(self._fetch)

    async def _fetch(self) -> dict[str, Any]:
        client = self._client or httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT, headers={"User-Agent": "Phoenix/0.1"}
        )
        try:
            feed = await self._json(client, FEED_URL)
            events = [
                f
                for f in feed["features"]
                if "shakemap" in (f["properties"].get("types") or "")
            ]
            # Strongest felt shaking first: that is where damage is likely
            events.sort(key=lambda f: f["properties"].get("mmi") or 0, reverse=True)
            events = events[:MAX_EVENTS]
            contour_sets = await asyncio.gather(
                *(self._contours(client, e) for e in events), return_exceptions=True
            )
        finally:
            if self._client is None:
                await client.aclose()

        features: list[dict[str, Any]] = []
        for event, contours in zip(events, contour_sets, strict=True):
            if isinstance(contours, BaseException):
                continue  # one broken ShakeMap must not hide the others
            props = event["properties"]
            for contour in contours:
                mmi = contour.get("properties", {}).get("value")
                if not isinstance(mmi, int | float) or mmi < MIN_CONTOUR_MMI:
                    continue
                features.append(
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": contour["geometry"]["type"],
                            "coordinates": round_coords(contour["geometry"]["coordinates"], 4),
                        },
                        "properties": {
                            "event_id": event["id"],
                            "mmi": mmi,
                            "color": contour["properties"].get("color"),
                            "magnitude": props.get("mag"),
                            "place": props.get("place"),
                            "max_mmi": props.get("mmi"),
                            "alert": props.get("alert"),
                            "time": props.get("time"),
                        },
                    }
                )
        return {
            "type": "FeatureCollection",
            "features": features,
            "source": "USGS ShakeMap",
            "earthquakes": len(events),
        }

    async def _contours(self, client: httpx.AsyncClient, event: dict[str, Any]) -> list[dict[str, Any]]:
        detail = await self._json(client, event["properties"]["detail"])
        shakemap = detail["properties"]["products"]["shakemap"][0]
        url = shakemap["contents"]["download/cont_mmi.json"]["url"]
        return (await self._json(client, url))["features"]

    @staticmethod
    async def _json(client: httpx.AsyncClient, url: str) -> Any:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()


usgs_shakemap_service = USGSShakeMapService()
