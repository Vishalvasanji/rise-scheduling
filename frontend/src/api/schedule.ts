import { api } from "./client";
import type {
  AuditEntry,
  DependencyType,
  ProjectOut,
  ProposalOut,
  ScheduleOut,
  TaskOut,
} from "../types/schedule";

export const listProjects = () => api.get<ProjectOut[]>("/projects");

export const getSchedule = (projectId: number) =>
  api.get<ScheduleOut>(`/projects/${projectId}/schedule`);

export type TaskEdit = Partial<TaskOut> & { expected_version?: number; force?: boolean };

export const updateTask = (taskId: number, fields: TaskEdit) =>
  api.patch<TaskOut>(`/tasks/${taskId}`, fields);

export const createTask = (projectId: number, fields: Partial<TaskOut>) =>
  api.post<TaskOut>(`/projects/${projectId}/tasks`, fields);

// One row's edits in a batched "Save all" (each `fields` carries its own
// expected_version for optimistic locking).
export interface BulkEdit {
  task_id: number;
  fields: TaskEdit;
}

// Apply a whole spreadsheet of edits at once → the recomputed schedule.
export const bulkUpdateTasks = (projectId: number, edits: BulkEdit[], force = false) =>
  api.post<ScheduleOut>(`/projects/${projectId}/tasks/bulk`, { edits, force });

export const deleteTask = (taskId: number) => api.del(`/tasks/${taskId}`);

export const createDependency = (
  predecessor_id: number,
  successor_id: number,
  type: DependencyType = "FS",
  lag_days = 0,
) => api.post("/dependencies", { predecessor_id, successor_id, type, lag_days });

export const deleteDependency = (dependencyId: number) =>
  api.del(`/dependencies/${dependencyId}`);

// ---- Pending "what-if" proposal (shared with chat) ----

export const getProposal = (projectId: number) =>
  api.get<ProposalOut | null>(`/projects/${projectId}/proposal`);

export const applyProposal = (projectId: number) =>
  api.post<ScheduleOut>(`/projects/${projectId}/proposal/apply`, {});

export const discardProposal = (projectId: number) =>
  api.post(`/projects/${projectId}/proposal/discard`, {});

export const undoLastChange = (projectId: number) =>
  api.post<ProposalOut | null>(`/projects/${projectId}/proposal/undo`, {});

// ---- Change activity (audit) ----

export const getAudit = (projectId: number, limit = 100) =>
  api.get<AuditEntry[]>(`/projects/${projectId}/audit?limit=${limit}`);
