import { clearToken, getToken } from './auth';
import { useProjectStore } from './project-store';

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
  ) {
    super(typeof detail === 'string' ? detail : `API ${status}`);
    this.name = 'ApiError';
  }
}

function buildHeaders(existing: HeadersInit | undefined): HeadersInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((existing as Record<string, string>) ?? {}),
  };
  const token = getToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  // Project scope — explicit pin, 'all' or 'auto'. Empty = backend default.
  if (typeof window !== 'undefined') {
    const active = useProjectStore.getState().activeProject;
    if (active) {
      headers['X-Axis-Project'] = active;
    }
  }
  return headers;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { ...init, headers: buildHeaders(init?.headers) });
  if (res.status === 401) {
    clearToken();
    if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
      window.location.href = '/login';
    }
  }
  if (!res.ok) {
    let detail: unknown = await res.text();
    try {
      detail = JSON.parse(detail as string);
      if (typeof detail === 'object' && detail !== null && 'detail' in detail) {
        detail = (detail as { detail: unknown }).detail;
      }
    } catch {
      /* not json */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => apiFetch<T>(path),
  post: <T>(path: string, body: unknown) =>
    apiFetch<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    apiFetch<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    apiFetch<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(path: string) => apiFetch<T>(path, { method: 'DELETE' }),
};
