import createClient, { type Middleware } from "openapi-fetch";
import type { paths, components } from "./schema.d.ts";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:28000";

type SnakeToCamel<S extends string> = S extends `${infer T}_${infer U}`
  ? `${T}${Capitalize<SnakeToCamel<U>>}`
  : S;

type CamelCaseKeys<T> =
  T extends Array<infer U>
    ? Array<CamelCaseKeys<U>>
    : T extends object
      ? {
          [K in keyof T as K extends string
            ? SnakeToCamel<K>
            : K]: CamelCaseKeys<T[K]>;
        }
      : T;

function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

function transformKeys<T>(obj: unknown): T {
  if (obj === null || obj === undefined) {
    return obj as T;
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => transformKeys(item)) as T;
  }

  if (typeof obj === "object") {
    const transformed: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
      const camelKey = snakeToCamel(key);
      transformed[camelKey] = transformKeys(value);
    }
    return transformed as T;
  }

  return obj as T;
}

class APIError extends Error {
  constructor(
    public statusCode: number,
    message: string,
  ) {
    super(message);
    this.name = "APIError";
  }
}

const camelCaseMiddleware: Middleware = {
  async onResponse({ response }) {
    if (!response.ok) {
      return response;
    }

    const contentType = response.headers.get("content-type");
    if (!contentType?.includes("application/json")) {
      return response;
    }

    const data = await response.json();
    const transformed = transformKeys(data);

    return new Response(JSON.stringify(transformed), {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  },
};

const client = createClient<paths>({
  baseUrl: API_URL,
  querySerializer: (params) => {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null) continue;
      if (Array.isArray(value)) {
        // FastAPI expects repeated keys for arrays: types=earthquake&types=flood
        value.forEach((v) => searchParams.append(key, String(v)));
      } else {
        searchParams.append(key, String(value));
      }
    }
    return searchParams.toString();
  },
});

client.use(camelCaseMiddleware);

export type ApiDisasterEvent = CamelCaseKeys<
  components["schemas"]["EventResponse"]
>;
export type ApiDisasterEventDetail = CamelCaseKeys<
  components["schemas"]["EventDetailResponse"]
>;
export type ApiEventListResponse = CamelCaseKeys<
  components["schemas"]["EventListResponse"]
>;
export type ApiGeoLayer = CamelCaseKeys<components["schemas"]["GeoLayerResponse"]>;
export type ApiDataSource = CamelCaseKeys<components["schemas"]["DataSourceRef"]>;
export type ApiDataset = CamelCaseKeys<components["schemas"]["DatasetResponse"]>;
export type ApiEventMetric = CamelCaseKeys<
  components["schemas"]["EventMetricResponse"]
>;
export type ApiLocation = CamelCaseKeys<components["schemas"]["Location"]>;
export type ApiPagination = CamelCaseKeys<components["schemas"]["Pagination"]>;
export type ApiGeoJSONFeatureCollection = CamelCaseKeys<
  components["schemas"]["GeoJSONFeatureCollection"]
>;

export type EventType = components["schemas"]["EventType"];
export type SeverityLevel = components["schemas"]["SeverityLevel"];

export interface EventFilter {
  /** Free-text search over title and region */
  q?: string;
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
  /** ISO time: only events ongoing at that instant (timeline) */
  at?: string;
}

export const eventsAPI = {
  list: async (
    filter?: EventFilter,
    limit = 50,
    offset = 0,
  ): Promise<ApiEventListResponse> => {
    const { data, error, response } = await client.GET("/api/v1/events", {
      params: {
        query: {
          q: filter?.q || undefined,
          types: filter?.types,
          severities: filter?.severities,
          start_date: filter?.startDate,
          end_date: filter?.endDate,
          min_lng: filter?.boundingBox?.minLng,
          min_lat: filter?.boundingBox?.minLat,
          max_lng: filter?.boundingBox?.maxLng,
          max_lat: filter?.boundingBox?.maxLat,
          is_active: filter?.isActive,
          at: filter?.at,
          limit,
          offset,
        },
      },
    });

    if (error) {
      throw new APIError(response.status, "Failed to fetch events");
    }

    return data as unknown as ApiEventListResponse;
  },

  get: async (id: string): Promise<ApiDisasterEventDetail> => {
    const { data, error, response } = await client.GET(
      "/api/v1/events/{event_id}",
      {
        params: {
          path: { event_id: id },
        },
      },
    );

    if (error) {
      throw new APIError(response.status, "Failed to fetch event");
    }

    return data as unknown as ApiDisasterEventDetail;
  },

  getLayers: async (id: string): Promise<{ layers: ApiGeoLayer[] }> => {
    const { data, error, response } = await client.GET(
      "/api/v1/events/{event_id}/layers",
      {
        params: {
          path: { event_id: id },
        },
      },
    );

    if (error) {
      throw new APIError(response.status, "Failed to fetch event layers");
    }

    return data as unknown as { layers: ApiGeoLayer[] };
  },
};

export const geodataAPI = {
  getGeoJSON: async (
    filter?: Omit<EventFilter, "boundingBox">,
  ): Promise<ApiGeoJSONFeatureCollection> => {
    const { data, error, response } = await client.GET(
      "/api/v1/geodata/events/geojson",
      {
        params: {
          query: {
            types: filter?.types,
            severities: filter?.severities,
            start_date: filter?.startDate,
            end_date: filter?.endDate,
            is_active: filter?.isActive,
          },
        },
      },
    );

    if (error) {
      throw new APIError(response.status, "Failed to fetch GeoJSON");
    }

    return data as unknown as ApiGeoJSONFeatureCollection;
  },
};

export type ApiSourceStatus = CamelCaseKeys<components["schemas"]["SourceStatus"]>;

export const sourcesAPI = {
  list: async (): Promise<ApiSourceStatus[]> => {
    const { data, response } = await client.GET("/api/v1/sources");
    // No error responses are declared for this endpoint, so check the status
    if (!response.ok) {
      throw new APIError(response.status, "Failed to fetch source status");
    }
    return data as unknown as ApiSourceStatus[];
  },
};

export type ApiTimeline = CamelCaseKeys<components["schemas"]["TimelineResponse"]>;
export type TimelineBucketSize = "hour" | "day" | "week";

export const timelineAPI = {
  get: async (
    start: string,
    end: string,
    bucket: TimelineBucketSize,
    filter?: Pick<EventFilter, "types" | "severities">,
  ): Promise<ApiTimeline> => {
    const { data, response } = await client.GET("/api/v1/events/timeline", {
      params: {
        query: { start, end, bucket, types: filter?.types, severities: filter?.severities },
      },
    });
    if (!response.ok) throw new APIError(response.status, "Failed to fetch timeline");
    return data as unknown as ApiTimeline;
  },
};

export type ApiViewSummary = CamelCaseKeys<components["schemas"]["ViewSummary"]>;
export type ApiNearby = CamelCaseKeys<components["schemas"]["NearbyResponse"]>;
type ViewFilter = Pick<EventFilter, "types" | "severities" | "at">;

/** What the current map view contains (G-5) */
export const viewAPI = {
  /** bbox is [west, south, east, north]; west > east crosses the antimeridian */
  summary: async (
    bbox: [number, number, number, number],
    filter?: ViewFilter,
    signal?: AbortSignal,
  ): Promise<ApiViewSummary> => {
    const [minLng, minLat, maxLng, maxLat] = bbox;
    const { data, response } = await client.GET("/api/v1/geodata/summary", {
      params: {
        query: {
          min_lng: minLng,
          min_lat: minLat,
          max_lng: maxLng,
          max_lat: maxLat,
          types: filter?.types,
          severities: filter?.severities,
          at: filter?.at,
        },
      },
      signal,
    });
    if (!response.ok) throw new APIError(response.status, "Failed to fetch view summary");
    return data as unknown as ApiViewSummary;
  },

  nearby: async (
    lat: number,
    lng: number,
    radiusKm: number,
    filter?: ViewFilter,
    signal?: AbortSignal,
  ): Promise<ApiNearby> => {
    const { data, response } = await client.GET("/api/v1/geodata/nearby", {
      params: {
        query: {
          lat,
          lng,
          radius_km: radiusKm,
          types: filter?.types,
          severities: filter?.severities,
          at: filter?.at,
        },
      },
      signal,
    });
    if (!response.ok) throw new APIError(response.status, "Failed to fetch nearby events");
    return data as unknown as ApiNearby;
  },
};

export type ApiAgentStatus = CamelCaseKeys<components["schemas"]["AgentStatus"]>;
export type ApiAgentReply = CamelCaseKeys<components["schemas"]["AgentChatResponse"]>;
export type ApiMapAction = ApiAgentReply["actions"][number];
export type AgentChatBody = components["schemas"]["AgentChatRequest"];

/** Map assistant (M4); status.enabled is false when the server has no model key */
export const agentAPI = {
  status: async (): Promise<ApiAgentStatus> => {
    const { data, response } = await client.GET("/api/v1/agent/status");
    if (!response.ok) throw new APIError(response.status, "Failed to fetch assistant status");
    return data as unknown as ApiAgentStatus;
  },

  chat: async (body: AgentChatBody, signal?: AbortSignal): Promise<ApiAgentReply> => {
    const { data, error, response } = await client.POST("/api/v1/agent/chat", { body, signal });
    if (!response.ok) {
      const detail = (error as { detail?: unknown } | undefined)?.detail;
      throw new APIError(response.status, typeof detail === "string" ? detail : "Assistant request failed");
    }
    return data as unknown as ApiAgentReply;
  },
};

export type ApiSatellitePass = CamelCaseKeys<components["schemas"]["SatellitePass"]>;

/** Moving things worth watching (M5) */
export const tracksAPI = {
  /** Earth-observation satellite passes over a place, soonest first */
  satellitePasses: async (lat: number, lng: number, hours = 24, signal?: AbortSignal): Promise<ApiSatellitePass[]> => {
    const { data, response } = await client.GET("/api/v1/tracks/satellites/passes", {
      params: { query: { lat, lng, hours } },
      signal,
    });
    if (!response.ok) throw new APIError(response.status, "Failed to fetch satellite passes");
    return (data as unknown as { passes: ApiSatellitePass[] }).passes;
  },
};

export type ApiNearbyCamera = CamelCaseKeys<components["schemas"]["NearbyCamera"]>;

/** Public cameras (M6); images always come through the API proxy */
export const camerasAPI = {
  nearby: async (lat: number, lng: number, radiusKm = 25, signal?: AbortSignal): Promise<ApiNearbyCamera[]> => {
    const { data, response } = await client.GET("/api/v1/cameras/nearby", {
      params: { query: { lat, lng, radius_km: radiusKm, limit: 5 } },
      signal,
    });
    if (!response.ok) throw new APIError(response.status, "Failed to fetch nearby cameras");
    return data as unknown as ApiNearbyCamera[];
  },
  snapshotUrl: (id: string, bust?: number) =>
    `${API_URL}/api/v1/cameras/${encodeURIComponent(id)}/snapshot${bust ? `?t=${bust}` : ""}`,
};

export const healthAPI = {
  check: async (): Promise<{ status: string }> => {
    const { data, error } = await client.GET("/health");

    if (error) {
      throw new APIError(500, "Health check failed");
    }

    return data as { status: string };
  },
};

export { client, APIError };
