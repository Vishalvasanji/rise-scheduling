// Small task helpers shared by the grid and the Gantt.

import type { TaskOut } from "../types/schedule";

// Has work on this task actually begun? Used to decide whether editing a start
// date is a PLAN change (sets the "start no earlier than" constraint) or an
// ACTUAL (sets actual_start). A task that hasn't started reschedules via the
// constraint, so a future start never gets logged as a fake actual.
export function isStarted(t: TaskOut): boolean {
  return (
    !!t.actual_start || t.percent_complete > 0 || t.status !== "not_started"
  );
}

// Overlay an in-progress spreadsheet draft onto a task for DISPLAY only. Edited
// cells show the typed values immediately; the real CPM dates (and any dependent
// shifts) recompute server-side on Save, so we also reflect a drafted start/finish
// into the shown planned_start/planned_finish.
export function applyDraft(t: TaskOut, d?: Partial<TaskOut>): TaskOut {
  if (!d) return t;
  const out: TaskOut = { ...t, ...d };
  if ("actual_start" in d && d.actual_start) out.planned_start = d.actual_start;
  else if ("start_no_earlier_than" in d && d.start_no_earlier_than)
    out.planned_start = d.start_no_earlier_than;
  if ("actual_finish" in d && d.actual_finish) out.planned_finish = d.actual_finish;
  return out;
}

// Editing a task's "From" (start) date: a not-yet-started task reschedules via the
// planning constraint (start_no_earlier_than); once work has begun it edits the
// actual start. Empty clears the field.
export function startFieldForEdit(t: TaskOut, iso: string): Partial<TaskOut> {
  return isStarted(t)
    ? { actual_start: iso || null }
    : { start_no_earlier_than: iso || null };
}
