import type { ShortcutKey } from "@/hooks/useKeyboardShortcuts";
import type { ViewMode } from "@/lib/map/viewModes";
import type { ShipCategory } from "@/lib/telemetry";
import type { RouteMode } from "@/store/routeStore";

export interface Translations {
  common: {
    close: string;
    menu: string;
    home: string;
    events: string;
    about: string;
    settings: string;
    search: string;
    searchPlaceholder: string;
    backToMap: string;
    loading: string;
    error: string;
    retry: string;
    viewOnMap: string;
  };
  sidebar: {
    layersAndFilters: string;
    eventTypes: string;
    severity: string;
    layers: string;
    // Event type labels
    earthquake: string;
    flood: string;
    wildfire: string;
    hurricane: string;
    tsunami: string;
    volcano: string;
    war: string;
    pollution: string;
    drought: string;
    other: string;
    landslide: string;
    industrial: string;
    epidemic: string;
    storm: string;
    coldwave: string;
    heatwave: string;
    complex_emergency: string;
    // Severity labels
    low: string;
    medium: string;
    high: string;
    critical: string;
    // Layer names
    disasterEvents: string;
    satelliteImagery: string;
    radar: string;
    cloudsInfrared: string;
    nightLights: string;
    cyclones: string;
    shakemaps: string;
    fires: string;
    powerPlants: string;
    dams: string;
    hospitals: string;
    submarineCables: string;
    satellites: string;
    aircraft: string;
    vessels: string;
    launches: string;
    cameras: string;
    /** Tooltip on layers that need an API key on the server */
    keyRequired: string;
    opacity: string;
    // Footer
    dataSource: string;
    eventsCount: string;
  };
  settings: {
    title: string;
    subtitle: string;
    language: string;
    languageDesc: string;
    displayLanguage: string;
    appearance: string;
    appearanceDesc: string;
    theme: string;
    enableAnimations: string;
    animationsDesc: string;
    mapPreferences: string;
    mapPreferencesDesc: string;
    defaultBasemap: string;
    defaultView: string;
    showClusterMarkers: string;
    clusterMarkersDesc: string;
    dataSync: string;
    dataSyncDesc: string;
    autoRefresh: string;
    autoRefreshDesc: string;
    refreshInterval: string;
    resetToDefaults: string;
    changesApplied: string;
    autoSaved: string;
  };
  about: {
    tagline: string;
    description: string;
    keyFeatures: string;
    dataSources: string;
    techStack: string;
    openSource: string;
    openSourceDesc: string;
    viewOnGithub: string;
    footer: string;
  };
  events: {
    title: string;
    eventsFound: string;
    noEvents: string;
    adjustFilters: string;
    clearFilters: string;
    affected: string;
    active: string;
    location: string;
    severity: string;
  };
  map: {
    globe3d: string;
    view2d: string;
    satellite: string;
    dark: string;
    activeEvents: string;
    initializingGlobe: string;
    live: string;
    reconnecting: string;
    share: string;
    linkCopied: string;
    engine3d: string;
    engine2d: string;
    engine3dKeyless: string;
    viewMode: string;
    viewModes: Record<ViewMode, string>;
  };
  sources: {
    title: string;
    fresh: string;
    stale: string;
    failing: string;
    never: string;
    /** Accessible summary, e.g. "USGS: Up to date" */
    summary: string;
  };
  timeline: {
    live: string;
    play: string;
    pause: string;
    speed: string;
    backToLive: string;
    scrub: string;
  };
  view: {
    inView: string;
    /** "{n} affected" */
    affected: string;
    /** "Updated {time}" */
    updated: string;
    nearby: string;
    noneNearby: string;
    /** Accessible name of the summary region */
    label: string;
  };
  brief: {
    play: string;
    pause: string;
    resume: string;
    prev: string;
    next: string;
    share: string;
    linkCopied: string;
    close: string;
    /** "Scene {n} of {total}" */
    scene: string;
    /** Generated scene captions; {title} is the event title */
    captions: {
      before: string;
      onset: string;
      now: string;
      context: string;
    };
  };
  agent: {
    open: string;
    title: string;
    placeholder: string;
    send: string;
    thinking: string;
    disabled: string;
    budgetSession: string;
    budgetDaily: string;
    error: string;
    /** "Map updated ({n})" */
    mapChanged: string;
    /** "{used} / {cap} tokens used" */
    usage: string;
    speak: string;
    stopListening: string;
    readAloud: string;
    micError: string;
    suggestions: {
      view: string;
      quakes: string;
      brief: string;
    };
  };
  satellites: {
    nextPasses: string;
    none: string;
    daylight: string;
    night: string;
  };
  cameras: {
    nearby: string;
    live: string;
    /** "Updates every {n} min" */
    updates: string;
    unavailable: string;
    notRecorded: string;
    approxView: string;
  };
  telemetry: {
    altitude: string;
    onGround: string;
    speed: string;
    heading: string;
    course: string;
    lastSeen: string;
    military: string;
    /** Military position generalised in a conflict zone */
    generalised: string;
    position: string;
    launchTime: string;
    status: string;
    provider: string;
    mission: string;
    orbit: string;
    pad: string;
    shipTypes: Record<ShipCategory, string>;
  };
  radio: {
    title: string;
    play: string;
    stop: string;
    offAir: string;
    open: string;
    source: string;
  };
  routing: {
    title: string;
    routeHere: string;
    mode: string;
    pickStart: string;
    planning: string;
    avoided: string;
    clear: string;
    /** "{km} km from route" */
    within: string;
    /** "{n} satellite fire detections ..." */
    fires: string;
    routerLimit: string;
    noDetour: string;
    disclaimer: string;
    modes: Record<RouteMode, string>;
  };
  ops: {
    label: string;
    follow: string;
    following: string;
    shortcuts: string;
    keys: Record<ShortcutKey, string>;
  };
}
