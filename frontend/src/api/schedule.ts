import { api } from "./client";
import type {
  DependencyType,
  ProjectOut,
  ScheduleOut,
  TaskOut,
} from "../types/schedule";

export const listProjects = () => api.get<ProjectOut[]>("/projects");

export const getSchedule = (projectId: number) =>
  api.get<ScheduleOut>(`/projects/${projectId}/schedule`);

export const updateTask = (taskId: number, fields: Partial<TaskOut>) =>
  api.patch<TaskOut>(`/tasks/${taskId}`, fields);

export const createTask = (projectId: number, fields: Partial<TaskOut>) =>
  api.post<TaskOut>(`/projects/${projectId}/tasks`, fields);

export const deleteTask = (taskId: number) => api.del(`/tasks/${taskId}`);

export const createDependency = (
  predecessor_id: number,
  successor_id: number,
  type: DependencyType = "FS",
  lag_days = 0,
) => api.post("/dependencies", { predecessor_id, successor_id, type, lag_days });
