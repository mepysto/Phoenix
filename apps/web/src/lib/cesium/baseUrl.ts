// Must be imported before "cesium": the engine reads CESIUM_BASE_URL when it
// first resolves its workers and assets (copied to public/cesium at build time).
if (typeof window !== "undefined") {
  (window as unknown as { CESIUM_BASE_URL?: string }).CESIUM_BASE_URL = "/cesium";
}

export {};
