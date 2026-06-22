// Mirrors the backend schemas (app/schemas). The backend computes all CPM
// fields (planned dates, float, is_critical); the frontend never recomputes.

export type TaskStatus =
  | "not_started"
  | "in_progress"
  | "complete"
  | "blocked";

export type DependencyType = "FS" | "SS" | "FF" | "SF";

export interface TaskOut {
  id: number;
  project_id: number;
  name: string;
  wbs: string | null;
  duration_days: number;
  percent_complete: number;
  status: TaskStatus;
  is_milestone: boolean;
  actual_start: string | null;
  actual_finish: string | null;
  planned_start: string | null;
  planned_finish: string | null;
  late_start: string | null;
  late_finish: string | null;
  total_float: number | null;
  free_float: number | null;
  is_critical: boolean;
  external_ref: string | null;
  procore_id: string | null;
}

export interface DependencyOut {
  id: number;
  predecessor_id: number;
  successor_id: number;
  type: DependencyType;
  lag_days: number;
  is_critical: boolean;
}

export interface ProjectOut {
  id: number;
  name: string;
  deal_type: string | null;
  units: number | null;
  stage: string | null;
  anchor_date: string;
  planned_start: string | null;
  planned_finish: string | null;
  external_ref: string | null;
  procore_id: string | null;
}

export interface ScheduleOut {
  project: ProjectOut;
  tasks: TaskOut[];
  dependencies: DependencyOut[];
}
