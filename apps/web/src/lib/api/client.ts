import type {
  EventFilter,
  EventListResponse,
  DisasterEventDetail,
  GeoLayer,
} from "@phoenix/shared/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:28000";

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
    message: string
  ) {
    super(message);
    this.name = "APIError";
  }
}

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: "Unknown error" }));
    throw new APIError(response.status, error.message || response.statusText);
  }

  const data = await response.json();
  return transformKeys<T>(data);
}

function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    if (Array.isArray(value)) {
      value.forEach((v) => searchParams.append(key, String(v)));
    } else {
      searchParams.append(key, String(value));
    }
  });
  const qs = searchParams.toString();
  return qs ? `?${qs}` : "";
}

export const eventsAPI = {
  list: async (
    filter?: EventFilter,
    limit = 50,
    offset = 0
  ): Promise<EventListResponse> => {
    const params: Record<string, unknown> = { limit, offset };
    if (filter?.types) params.types = filter.types;
    if (filter?.severities) params.severities = filter.severities;
    if (filter?.startDate) params.start_date = filter.startDate;
    if (filter?.endDate) params.end_date = filter.endDate;
    if (filter?.boundingBox) {
      params.min_lng = filter.boundingBox.minLng;
      params.min_lat = filter.boundingBox.minLat;
      params.max_lng = filter.boundingBox.maxLng;
      params.max_lat = filter.boundingBox.maxLat;
    }
    if (filter?.isActive !== undefined) params.is_active = filter.isActive;

    return fetchAPI<EventListResponse>(`/api/v1/events${buildQueryString(params)}`);
  },

  get: async (id: string): Promise<DisasterEventDetail> => {
    return fetchAPI<DisasterEventDetail>(`/api/v1/events/${id}`);
  },

  getLayers: async (id: string): Promise<{ layers: GeoLayer[] }> => {
    return fetchAPI<{ layers: GeoLayer[] }>(`/api/v1/events/${id}/layers`);
  },
};

export const healthAPI = {
  check: async (): Promise<{ status: string }> => {
    return fetchAPI<{ status: string }>("/health");
  },
};

export { APIError };
