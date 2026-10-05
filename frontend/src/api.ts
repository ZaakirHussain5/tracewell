import type { Overview, TraceDetail } from "./types";

const base = import.meta.env.VITE_API_BASE ?? "";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${base}${path}`);
  if (!response.ok) {
    let detail = `${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Keep the status when the body is not JSON.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export function fetchOverview(params: URLSearchParams): Promise<Overview> {
  const query = params.toString();
  return getJson<Overview>(`/api/overview${query ? `?${query}` : ""}`);
}

export function fetchTrace(traceId: string): Promise<TraceDetail> {
  return getJson<TraceDetail>(`/api/traces/${encodeURIComponent(traceId)}`);
}
