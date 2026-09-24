/** Where the MapLibre worker is served from (copied by scripts/copy-map-assets.mjs) */
export const MAPLIBRE_WORKER_URL = "/maplibre/maplibre-gl-worker.mjs";

/** Call once before creating a map: bundlers cannot locate MapLibre 6's worker themselves */
export function configureMaplibreWorker(maplibregl: { setWorkerUrl: (url: string) => void }): void {
  maplibregl.setWorkerUrl(MAPLIBRE_WORKER_URL);
}
