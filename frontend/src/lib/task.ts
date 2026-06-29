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
