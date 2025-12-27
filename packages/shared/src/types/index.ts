export type EventType =
  | 'earthquake'
  | 'flood'
  | 'wildfire'
  | 'hurricane'
  | 'tsunami'
  | 'volcano'
  | 'war'
  | 'pollution'
  | 'drought'
  | 'other';

export type SeverityLevel = 'low' | 'medium' | 'high' | 'critical';

export interface GeoJSONPoint {
  type: 'Point';
  coordinates: [longitude: number, latitude: number];
}

export interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

export interface GeoJSONMultiPolygon {
  type: 'MultiPolygon';
  coordinates: number[][][][];
}

export type GeoJSONGeometry = GeoJSONPoint | GeoJSONPolygon | GeoJSONMultiPolygon;

export interface Location {
  lat: number;
  lng: number;
  country?: string;
  countryCode?: string;
  region?: string;
}

export interface DataSource {
  id: string;
  name: string;
  type: 'gdacs' | 'copernicus' | 'unosat' | 'hdx' | 'user';
  url?: string;
}

export interface DisasterEvent {
  id: string;
  type: EventType;
  title: string;
  description?: string;
  location: Location;
  severity: SeverityLevel;
  affectedPopulation?: number;
  affectedAreaKm2?: number;
  startDate: string;
  endDate?: string;
  isActive: boolean;
  sources: DataSource[];
  geometry?: GeoJSONGeometry;
  createdAt: string;
  updatedAt: string;
}

export interface EventListResponse {
  data: DisasterEvent[];
  pagination: Pagination;
}

export interface DisasterEventDetail extends DisasterEvent {
  layers: GeoLayer[];
  datasets: Dataset[];
  metrics: EventMetric[];
}

export interface GeoLayer {
  id: string;
  eventId: string;
  layerType: string;
  geometry: GeoJSONGeometry;
  properties: Record<string, unknown>;
  timestamp?: string;
}

export interface Dataset {
  id: string;
  eventId: string;
  name: string;
  type: 'satellite_image' | 'vector' | '3d_tiles' | 'report' | 'other';
  url?: string;
  license?: string;
  metadata?: Record<string, unknown>;
}

export interface EventMetric {
  time: string;
  eventId: string;
  metricType: string;
  value: number;
}

export interface Pagination {
  total: number;
  limit: number;
  offset: number;
  hasMore: boolean;
}

export interface APIError {
  error: string;
  message: string;
  statusCode: number;
  details?: Record<string, unknown>;
}

export interface ViewerConfig {
  mode: '2d' | '3d';
  baseLayer: 'osm' | 'satellite' | 'terrain';
  terrain: {
    enabled: boolean;
    provider: 'cesium-world-terrain' | 'custom';
    exaggeration?: number;
  };
  buildings: {
    enabled: boolean;
    tilesetUrl?: string;
  };
}

export interface LayerConfig {
  id: string;
  name: string;
  type: string;
  visible: boolean;
  opacity: number;
  order: number;
}

export interface EventFilter {
  types?: EventType[];
  severities?: SeverityLevel[];
  startDate?: string;
  endDate?: string;
  boundingBox?: {
    minLng: number;
    minLat: number;
    maxLng: number;
    maxLat: number;
  };
  isActive?: boolean;
}
