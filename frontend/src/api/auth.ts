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

export interface ConnectorToken {
  token: string;
  connector_url: string;
}

// Mint this user's long-lived Claude.ai connector token (Bearer auth).
export const getConnectorToken = () =>
  api.post<ConnectorToken>("/auth/connector-token", {});

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export const hasToken = () => !!localStorage.getItem(TOKEN_KEY);
