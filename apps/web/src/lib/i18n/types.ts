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
}
