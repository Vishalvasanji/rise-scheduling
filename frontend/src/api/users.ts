import { api } from "./client";

export interface UserRow {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  project_ids: number[];
}

export interface NewUser {
  email: string;
  password: string;
  full_name?: string | null;
  role: string;
  project_ids: number[];
}

export const listUsers = () => api.get<UserRow[]>("/users");

export const createUser = (body: NewUser) => api.post<UserRow>("/users", body);

export const updateUser = (
  id: number,
  body: { full_name?: string | null; role?: string; password?: string },
) => api.patch<UserRow>(`/users/${id}`, body);

export const setUserProjects = (id: number, project_ids: number[]) =>
  api.put<UserRow>(`/users/${id}/projects`, { project_ids });

export const deleteUser = (id: number) => api.del(`/users/${id}`);
