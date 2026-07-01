import { api } from "./client";

const TOKEN_KEY = "rise_token";

export interface Me {
  email: string;
  full_name: string | null;
  role: string;
  is_admin: boolean;
  project_ids: number[];
}

export async function login(email: string, password: string): Promise<void> {
  const r = await api.post<{ access_token: string }>("/auth/login", { email, password });
  localStorage.setItem(TOKEN_KEY, r.access_token);
}

export const getMe = () => api.get<Me>("/auth/me");

// The MCP URL to paste into Claude.ai's custom connector (OAuth; no token to copy).
export const getConnectorUrl = () =>
  api.get<{ connector_url: string }>("/auth/connector-url");

// Whether this user's Claude connector is live (drives the header status pill).
export const getClaudeStatus = () =>
  api.get<{ connected: boolean }>("/auth/claude-status");

// Wake the (free-tier, sleeps-when-idle) MCP connector server so it's ready before
// the user connects from Claude. May block for a cold start; resolves ready:false
// if the server can't be reached.
export const warmConnector = () =>
  api.get<{ ready: boolean }>("/auth/connector-warm");

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export const hasToken = () => !!localStorage.getItem(TOKEN_KEY);
