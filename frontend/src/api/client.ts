export type HealthStatus = "ok" | "unavailable";

export interface HealthResponse {
  status: string;
  service?: string;
}

/** Typed API boundary. Feature-specific endpoints will be added with the backend tasks. */
export interface ApiClient {
  getHealth: () => Promise<HealthResponse>;
  getOperationsHealth: () => Promise<OperationsHealth>;
  getSources: () => Promise<SourceSummary[]>;
  getExecutions: () => Promise<ExecutionSummary[]>;
  getMetrics: () => Promise<OperationsMetrics>;
  refresh: () => Promise<ExecutionSummary>;
}

export interface OperationsHealth {
  status: "ok" | "degraded" | "error" | string;
  checked_at?: string;
  checks: Record<string, { status: string; message?: string; model?: string }>;
}

export interface SourceSummary {
  id: number;
  name: string;
  kind: string;
  base_url: string;
  enabled: boolean;
  robots_checked_at?: string | null;
}

export interface ExecutionSummary {
  id?: number;
  run_id: string;
  status: string;
  started_at?: string;
  finished_at?: string | null;
  metrics: { jobs_found?: number; sources_failed?: number; [key: string]: number | string | undefined };
  error?: string | null;
}

export interface OperationsMetrics {
  jobs: { total: number; active: number };
  sources: { total: number; enabled: number };
  executions: { total: number; running: number };
  generated_at?: string;
}

export function createApiClient(baseUrl = ""): ApiClient {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${baseUrl}${path}`, init);
    if (!response.ok) throw new Error(`API request failed (${response.status})`);
    return (await response.json()) as T;
  }
  return {
    async getHealth() {
      const response = await fetch(`${baseUrl}/health`);
      if (!response.ok) throw new Error(`API request failed (${response.status})`);
      return (await response.json()) as HealthResponse;
    },
    getOperationsHealth: async () => request<OperationsHealth>("/api/v1/operations/health"),
    getSources: async () => (await request<{ items: SourceSummary[] }>("/api/v1/operations/sources")).items,
    getExecutions: async () => (await request<{ items: ExecutionSummary[] }>("/api/v1/operations/executions?page_size=10")).items,
    getMetrics: async () => request<OperationsMetrics>("/api/v1/operations/metrics"),
    refresh: async () => request<ExecutionSummary>("/api/v1/operations/refresh", { method: "POST" }),
  };
}
