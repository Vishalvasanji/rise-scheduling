// Minimal fetch wrapper around the FastAPI JSON API. Surfaces the backend's
// structured engine errors (circular_dependency / date_conflict) so the UI can
// revert optimistic edits and explain why.

const BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown, message: string) {
    super(message);
    this.status = status;
    this.body = body;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem("rise_token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  if (resp.status === 204) return undefined as T;

  const body = await resp.json().catch(() => undefined);
  if (!resp.ok) {
    const message =
      (body && (body.detail || body.message || body.error)) ||
      `Request failed (${resp.status})`;
    throw new ApiError(resp.status, body, String(message));
  }
  return body as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(data) }),
  patch: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "PATCH", body: JSON.stringify(data) }),
  put: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "PUT", body: JSON.stringify(data) }),
  del: (path: string) => request<void>(path, { method: "DELETE" }),
};
