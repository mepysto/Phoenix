"use client";

import { useEffect } from "react";
import type { GeoJSONSource, MapMouseEvent } from "maplibre-gl";
import { AlertTriangle, Flame, Navigation, X } from "lucide-react";
import { routingAPI } from "@/lib/api/client";
import { useTranslation } from "@/lib/i18n/useTranslation";
import { getMapInstance } from "@/lib/map/mapInstance";
import { useRouteStore, type RouteMode } from "@/store/routeStore";

const SOURCE = "phoenix-route";
const MODES: RouteMode[] = ["auto", "truck", "pedestrian", "bicycle"];
const EMPTY: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };

/** Draw (or clear) the route and its end points on the map */
function draw(collection: GeoJSON.FeatureCollection, danger: boolean) {
  const map = getMapInstance();
  if (!map) return;
  const source = map.getSource(SOURCE) as GeoJSONSource | undefined;
  if (source) {
    source.setData(collection);
  } else {
    map.addSource(SOURCE, { type: "geojson", data: collection });
    map.addLayer({
      id: `${SOURCE}-line`,
      type: "line",
      source: SOURCE,
      filter: ["==", ["geometry-type"], "LineString"],
      layout: { "line-cap": "round", "line-join": "round" },
      paint: { "line-color": "#22d3ee", "line-width": 5, "line-opacity": 0.9 },
    });
    map.addLayer({
      id: `${SOURCE}-ends`,
      type: "circle",
      source: SOURCE,
      filter: ["==", ["geometry-type"], "Point"],
      paint: { "circle-radius": 6, "circle-color": "#ffffff", "circle-stroke-color": "#0e7490", "circle-stroke-width": 3 },
    });
  }
  // Red when the route passes through hazard zones
  map.setPaintProperty(`${SOURCE}-line`, "line-color", danger ? "#f87171" : "#22d3ee");
}

/** Plan a hazard-aware route to a destination chosen from an event */
export function RoutePlanner() {
  const { t } = useTranslation();
  const { start, end, mode, pickingStart, result, loading, error, setStart, setMode, setResult, setLoading, clear } =
    useRouteStore();

  // Pick the start with a map click
  useEffect(() => {
    // The planner opens from the event card, so the map is ready by then
    const map = getMapInstance();
    if (!pickingStart || !map) return;
    map.getCanvas().style.cursor = "crosshair";
    const onClick = (e: MapMouseEvent) => setStart({ lat: e.lngLat.lat, lng: e.lngLat.lng });
    map.once("click", onClick);
    return () => {
      map.off("click", onClick);
      map.getCanvas().style.cursor = "";
    };
  }, [pickingStart, setStart]);

  // Fetch the route when both ends and the mode are known
  useEffect(() => {
    if (!start || !end) return;
    const controller = new AbortController();
    setLoading(true);
    routingAPI
      .route({ start, end, mode, avoid_hazards: true }, controller.signal)
      .then((route) => setResult(route))
      .catch((e: Error) => {
        if (!controller.signal.aborted) setResult(null, e.message);
      });
    return () => controller.abort();
  }, [start, end, mode, setLoading, setResult]);

  // Keep the drawing in step with the result
  useEffect(() => {
    const features: GeoJSON.Feature[] = [];
    if (result) features.push({ type: "Feature", geometry: result.geometry as GeoJSON.LineString, properties: {} });
    for (const point of [start, end]) {
      if (point) features.push({ type: "Feature", geometry: { type: "Point", coordinates: [point.lng, point.lat] }, properties: {} });
    }
    draw(features.length ? { type: "FeatureCollection", features } : EMPTY, (result?.hazards.length ?? 0) > 0);
  }, [result, start, end]);

  if (!end) return null;
  const note =
    result?.avoidanceNote === "router_limit"
      ? t.routing.routerLimit
      : result?.avoidanceNote === "no_detour"
        ? t.routing.noDetour
        : null;

  return (
    <section
      aria-label={t.routing.title}
      className="pointer-events-auto w-80 rounded-lg bg-gray-900/95 text-sm text-gray-200 shadow-xl backdrop-blur"
    >
      <header className="flex items-center gap-2 px-3 py-2">
        <Navigation className="h-4 w-4 text-cyan-300" aria-hidden="true" />
        <h2 className="min-w-0 flex-1 truncate font-semibold text-white">
          {t.routing.title}
          {end.label ? `: ${end.label}` : ""}
        </h2>
        <button type="button" onClick={clear} className="rounded p-1 hover:bg-gray-800" aria-label={t.common.close}>
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </header>
      <div className="space-y-2 border-t border-gray-700/60 px-3 py-2 text-xs">
        <select
          value={mode}
          onChange={(e) => setMode(e.target.value as RouteMode)}
          aria-label={t.routing.mode}
          className="w-full rounded bg-gray-800 px-2 py-1 text-gray-100"
        >
          {MODES.map((m) => (
            <option key={m} value={m}>
              {t.routing.modes[m]}
            </option>
          ))}
        </select>
        {pickingStart && <p className="text-cyan-300">{t.routing.pickStart}</p>}
        {loading && <p className="text-gray-400">{t.routing.planning}</p>}
        {error && <p className="text-red-300">{error}</p>}
        {result && !loading && (
          <>
            <p className="font-mono text-gray-100">
              {result.distanceKm?.toFixed(1)} km · {Math.round(result.durationMin ?? 0)} min
              {result.avoided && <span className="ml-2 text-green-300">{t.routing.avoided}</span>}
            </p>
            {result.hazards.length === 0 ? (
              <p className="text-green-300">{t.routing.clear}</p>
            ) : (
              <ul className="space-y-1">
                {result.hazards.map((hazard) => (
                  <li key={hazard.id} className="flex items-start gap-1.5 text-red-200">
                    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                    <span className="flex-1">
                      {hazard.title}
                      <span className="text-gray-400">
                        {" "}
                        · {t.sidebar[hazard.severity as "high" | "critical"] ?? hazard.severity} ·{" "}
                        {t.routing.within.replace("{km}", String(hazard.distanceKm))}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {result.firesNearRoute > 0 && (
              <p className="flex items-center gap-1.5 text-orange-300">
                <Flame className="h-3.5 w-3.5" aria-hidden="true" />
                {t.routing.fires.replace("{n}", String(result.firesNearRoute))}
              </p>
            )}
            {note && <p className="text-amber-300">{note}</p>}
            <p className="text-[11px] text-gray-500">{t.routing.disclaimer}</p>
          </>
        )}
      </div>
    </section>
  );
}
