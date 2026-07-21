export type HealthStatus = "ok" | "unavailable";

export interface HealthResponse {
  status: string;
  service?: string;
}

export interface ApiClient {
  getHealth: () => Promise<HealthResponse>;
  getOperationsHealth: () => Promise<OperationsHealth>;
  getSources: () => Promise<SourceSummary[]>;
  getExecutions: () => Promise<ExecutionSummary[]>;
  getMetrics: () => Promise<OperationsMetrics>;
  refresh: () => Promise<ExecutionSummary>;
  listJobs: (params?: JobListParams) => Promise<PaginatedJobsResponse>;
  getJobDetail: (jobId: number) => Promise<JobDetailResponse>;
  createSource: (data: SourceCreateRequest) => Promise<SourceSummary>;
  updateSource: (sourceId: number, data: SourceUpdateRequest) => Promise<SourceSummary>;
  getProfile: (profileId: number) => Promise<ProfileResponse>;
  updateProfile: (profileId: number, data: ProfileUpdatePayload) => Promise<ProfileResponse>;
  updateProfilePreferences: (profileId: number, data: PreferencePayload) => Promise<ProfileResponse>;
  uploadProfile: (file: File) => Promise<UploadResponse>;
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

export interface SourceCreateRequest {
  name: string;
  kind?: string;
  base_url?: string;
  enabled?: boolean;
  config?: Record<string, unknown>;
}

export interface SourceUpdateRequest {
  enabled?: boolean;
  name?: string;
  base_url?: string;
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

export interface JobSummary {
  id: number;
  title: string;
  company: string;
  region: string;
  modality: string;
  status: string;
  description_url: string;
  application_url: string | null;
  published_at: string | null;
  score: number | null;
}

export interface JobDetailResponse extends JobSummary {
  description: string;
  canonical_url: string;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string | null;
  score_breakdown: Record<string, unknown>;
  recommendations: string[];
  evaluation: JobEvaluation | null;
}

export interface JobEvaluation {
  id: number;
  profile_id: number;
  score: number;
  score_breakdown: Record<string, unknown>;
  matches: unknown[];
  gaps: unknown[];
  recommendations: unknown[];
  status: string;
  evaluated_at: string | null;
}

export interface PaginatedJobsResponse {
  items: JobSummary[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ProfileResponse {
  id: number;
  name: string;
  cv_text: string | null;
  cv_filename: string | null;
  version: number;
  seniority: string | null;
  reevaluation_required: boolean;
  reevaluation_reason: string | null;
  reevaluation_metadata: Record<string, unknown>;
  versioned_at: string | null;
  skills: unknown[];
  experience: unknown[];
  education: unknown[];
  languages: unknown[];
  preferences: PreferenceResponse | null;
}

export interface ProfileUpdatePayload {
  name?: string;
  seniority?: string;
  skills?: unknown[];
  experience?: unknown[];
  education?: unknown[];
  languages?: unknown[];
}

export interface PreferencePayload {
  target_roles?: string[];
  locations?: string[];
  modalities?: string[];
  seniority?: string | null;
  preferred_languages?: string[];
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  salary_period?: string | null;
  employment_types?: string[];
  work_authorization?: string[];
  willing_to_relocate?: boolean;
  excluded_constraints?: string[];
  weights?: Record<string, number>;
}

export interface PreferenceResponse extends PreferencePayload {
  id: number;
  profile_id: number;
  is_current: boolean;
  created_at: string;
}

export interface UploadResponse extends ProfileResponse {
  parsed_text_length: number;
}

export interface JobListParams {
  page?: number;
  page_size?: number;
  region?: string;
  modality?: string;
  status?: string;
  company?: string;
  min_score?: number;
  order?: string;
  direction?: string;
}

export function createApiClient(baseUrl = ""): ApiClient {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${baseUrl}${path}`, init);
    if (!response.ok) throw new Error(`API request failed (${response.status})`);
    return (await response.json()) as T;
  }

  function buildQuery(params?: Record<string, string | number | undefined>): string {
    if (!params) return "";
    const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
    if (entries.length === 0) return "";
    return "?" + entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join("&");
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
    listJobs: async (params) => request<PaginatedJobsResponse>(`/api/v1/jobs${buildQuery(params as Record<string, string | number | undefined>)}`),
    getJobDetail: async (jobId) => request<JobDetailResponse>(`/api/v1/jobs/${jobId}`),
    createSource: async (data) => request<SourceSummary>("/api/v1/operations/sources", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }),
    updateSource: async (sourceId, data) => request<SourceSummary>(`/api/v1/operations/sources/${sourceId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }),
    getProfile: async (profileId) => request<ProfileResponse>(`/api/v1/profiles/${profileId}`),
    updateProfile: async (profileId, data) => request<ProfileResponse>(`/api/v1/profiles/${profileId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }),
    updateProfilePreferences: async (profileId, data) => request<ProfileResponse>(`/api/v1/profiles/${profileId}/preferences`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }),
    async uploadProfile(file: File) {
      const form = new FormData();
      form.append("file", file);
      const response = await fetch(`${baseUrl}/api/v1/profiles/upload`, { method: "POST", body: form });
      if (!response.ok) throw new Error(`API request failed (${response.status})`);
      return (await response.json()) as UploadResponse;
    },
  };
}
