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

export interface LeadershipDigest {
  type: string;
  projects: {
    project_id: number;
    name: string;
    stage: string | null;
    units: number | null;
    planned_start: string | null;
    planned_finish: string | null;
    task_count: number;
    critical_count: number;
    percent_complete: number;
    slipped_count: number;
  }[];
}

export const getLeadershipDigest = () =>
  api.get<LeadershipDigest>("/reports/leadership-digest");
