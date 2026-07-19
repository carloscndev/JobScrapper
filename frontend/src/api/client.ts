export type HealthStatus = "ok" | "unavailable";

export interface HealthResponse {
  status: string;
  service?: string;
}

/** Typed API boundary. Feature-specific endpoints will be added with the backend tasks. */
export interface ApiClient {
  getHealth: () => Promise<HealthResponse>;
}

export function createApiClient(baseUrl = ""): ApiClient {
  return {
    async getHealth() {
      const response = await fetch(`${baseUrl}/health`);
      if (!response.ok) throw new Error(`API request failed (${response.status})`);
      return (await response.json()) as HealthResponse;
    },
  };
}
