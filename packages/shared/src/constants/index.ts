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
};

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
};

export const SEVERITY_COLORS: Record<SeverityLevel, string> = {
  low: '#22C55E',
  medium: '#F59E0B',
  high: '#EF4444',
  critical: '#7C3AED',
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
