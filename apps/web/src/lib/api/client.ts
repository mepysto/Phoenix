import createClient, { type Middleware } from "openapi-fetch";
import type { paths, components } from "./schema.d.ts";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:28000";

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
  components["schemas"]["DisasterEvent"]
>;
export type ApiDisasterEventDetail = CamelCaseKeys<
  components["schemas"]["DisasterEventDetail"]
>;
export type ApiEventListResponse = CamelCaseKeys<
  components["schemas"]["EventListResponse"]
>;
export type ApiGeoLayer = CamelCaseKeys<components["schemas"]["GeoLayer"]>;
export type ApiDataSource = CamelCaseKeys<components["schemas"]["DataSource"]>;
export type ApiDataset = CamelCaseKeys<components["schemas"]["Dataset"]>;
export type ApiEventMetric = CamelCaseKeys<
  components["schemas"]["EventMetric"]
>;
export type ApiLocation = CamelCaseKeys<components["schemas"]["Location"]>;
export type ApiPagination = CamelCaseKeys<components["schemas"]["Pagination"]>;
export type ApiGeoJSONFeatureCollection = CamelCaseKeys<
  components["schemas"]["GeoJSONFeatureCollection"]
>;

export type EventType = components["schemas"]["DisasterEvent"]["type"];
export type SeverityLevel = components["schemas"]["DisasterEvent"]["severity"];

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

export const eventsAPI = {
  list: async (
    filter?: EventFilter,
    limit = 50,
    offset = 0,
  ): Promise<ApiEventListResponse> => {
    const { data, error, response } = await client.GET("/api/v1/events", {
      params: {
        query: {
          types: filter?.types,
          severities: filter?.severities,
          start_date: filter?.startDate,
          end_date: filter?.endDate,
          min_lng: filter?.boundingBox?.minLng,
          min_lat: filter?.boundingBox?.minLat,
          max_lng: filter?.boundingBox?.maxLng,
          max_lat: filter?.boundingBox?.maxLat,
          is_active: filter?.isActive,
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
      "/api/v1/geodata/geojson",
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

export const healthAPI = {
  check: async (): Promise<{ status: string }> => {
    const { data, error } = await client.GET("/health");

    if (error) {
      throw new APIError(500, "Health check failed");
    }

    return data as { status: string };
  },
};

export const syncAPI = {
  syncGDACS: async () => {
    const { data, error } = await client.POST("/api/v1/sync/gdacs");

    if (error) {
      throw new APIError(500, "GDACS sync failed");
    }

    return data;
  },

  syncCopernicus: async () => {
    const { data, error } = await client.POST("/api/v1/sync/copernicus");

    if (error) {
      throw new APIError(500, "Copernicus sync failed");
    }

    return data;
  },
};

export { client, APIError };
