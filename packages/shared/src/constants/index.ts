import type { EventType, SeverityLevel } from '../types';

export const EVENT_TYPE_LABELS: Record<EventType, string> = {
  earthquake: 'Earthquake',
  flood: 'Flood',
  wildfire: 'Wildfire',
  hurricane: 'Hurricane/Typhoon',
  tsunami: 'Tsunami',
  volcano: 'Volcanic Eruption',
  war: 'Armed Conflict',
  pollution: 'Environmental Pollution',
  drought: 'Drought',
  other: 'Other',
  landslide: 'Landslide',
  industrial: 'Industrial Accident',
  epidemic: 'Epidemic',
  storm: 'Severe Storm',
  coldwave: 'Cold Wave',
  heatwave: 'Heat Wave',
  complex_emergency: 'Complex Emergency',
};

/** Every event type the API can return (mirrors the backend EventType enum). */
export const EVENT_TYPES = Object.keys(EVENT_TYPE_LABELS) as EventType[];

export const EVENT_TYPE_COLORS: Record<EventType, string> = {
  earthquake: '#8B4513',
  flood: '#1E90FF',
  wildfire: '#FF4500',
  hurricane: '#9400D3',
  tsunami: '#00CED1',
  volcano: '#DC143C',
  war: '#2F4F4F',
  pollution: '#32CD32',
  drought: '#DAA520',
  other: '#808080',
  landslide: '#A0522D',
  industrial: '#708090',
  epidemic: '#C71585',
  storm: '#4682B4',
  coldwave: '#87CEEB',
  heatwave: '#FF8C00',
  complex_emergency: '#556B2F',
};

/**
 * Severity colours for canvas and map paint (dark surfaces). DOM styles use
 * the theme-aware CSS variables --sev-* (apps/web globals.css) instead.
 * Low is blue, not green: green next to amber failed the colour-vision check.
 */
export const SEVERITY_COLORS: Record<SeverityLevel, string> = {
  low: '#3987E5',
  medium: '#C98500',
  high: '#E5484D',
  critical: '#9085E9',
};

export const SEVERITY_LABELS: Record<SeverityLevel, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
};

export const MAP_CONFIG = {
  DEFAULT_CENTER: { lng: 0, lat: 20 },
  DEFAULT_ZOOM: 2,
  MIN_ZOOM: 1,
  MAX_ZOOM: 18,
  TILE_SIZE: 256,
} as const;

export const API_CONFIG = {
  DEFAULT_PAGE_SIZE: 50,
  MAX_PAGE_SIZE: 200,
  REQUEST_TIMEOUT_MS: 30000,
} as const;

export const DATA_SOURCES = {
  GDACS: {
    name: 'GDACS',
    fullName: 'Global Disaster Alert and Coordination System',
    apiUrl: 'https://www.gdacs.org/gdacsapi/api',
    rssUrl: 'https://www.gdacs.org/xml/rss.xml',
    website: 'https://www.gdacs.org',
  },
  COPERNICUS: {
    name: 'Copernicus EMS',
    fullName: 'Copernicus Emergency Management Service',
    apiUrl: 'https://emergency.copernicus.eu',
    website: 'https://emergency.copernicus.eu',
  },
  HDX: {
    name: 'HDX',
    fullName: 'Humanitarian Data Exchange',
    apiUrl: 'https://data.humdata.org/api/3',
    website: 'https://data.humdata.org',
  },
  UNOSAT: {
    name: 'UNOSAT',
    fullName: 'UN Satellite Centre',
    website: 'https://unosat.org',
  },
} as const;

export const GDACS_EVENT_TYPE_MAP: Record<string, EventType> = {
  EQ: 'earthquake',
  FL: 'flood',
  TC: 'hurricane',
  VO: 'volcano',
  DR: 'drought',
  WF: 'wildfire',
  TS: 'tsunami',
};

export const GDACS_SEVERITY_MAP: Record<string, SeverityLevel> = {
  Green: 'low',
  Orange: 'medium',
  Red: 'high',
};
