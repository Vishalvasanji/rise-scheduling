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
  trade: string | null;
  building: string | null;
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
  wbs_labels: Record<string, string> | null;
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

// ---- Pending "what-if" proposals (sandbox preview from chat or the API) ----

export type ChangeType = "new" | "removed" | "moved" | "modified";

export interface ChangeSide {
  planned_start: string | null;
  planned_finish: string | null;
  duration_days: number | null;
}

export interface TaskChange {
  task_id: number;
  name: string;
  change_type: ChangeType;
  current: ChangeSide | null;
  proposed: ChangeSide | null;
}

export interface ProposalStep {
  summary: string | null;
  change_count: number | null;
  created_at: string | null;
}

export interface ProposalOut {
  summary: string | null;
  actor: string | null;
  created_at: string | null;
  schedule: ScheduleOut; // the proposed (computed) schedule
  changes: TaskChange[];
  steps: ProposalStep[]; // the staged steps, in order (proposal accumulates)
}
