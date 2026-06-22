// Fetches a project's schedule and exposes mutations with optimistic-ish
// behaviour: on any engine rejection (cycle / date conflict) we refetch so the
// UI reverts to the server's authoritative state and surfaces the error.

import { useCallback, useEffect, useState } from "react";
import {
  deleteTask as apiDeleteTask,
  getSchedule,
  updateTask as apiUpdateTask,
} from "../api/schedule";
import { ApiError } from "../api/client";
import type { ScheduleOut, TaskOut } from "../types/schedule";

export function useSchedule(projectId: number | null) {
  const [schedule, setSchedule] = useState<ScheduleOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (projectId == null) return;
    setLoading(true);
    try {
      setSchedule(await getSchedule(projectId));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load schedule");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const mutate = useCallback(
    async (fn: () => Promise<unknown>) => {
      try {
        await fn();
        setError(null);
      } catch (e) {
        if (e instanceof ApiError && e.body && typeof e.body === "object") {
          const b = e.body as Record<string, unknown>;
          if (b.error === "circular_dependency")
            setError(`Rejected: that link would create a cycle (${(b.cycle as number[]).join(" → ")}).`);
          else if (b.error === "date_conflict")
            setError(`Rejected: ${b.reason ?? "date conflict"}.`);
          else setError(e.message);
        } else {
          setError(e instanceof Error ? e.message : "Update failed");
        }
      } finally {
        await refresh(); // always reconcile with the authoritative server state
      }
    },
    [refresh],
  );

  const updateTask = useCallback(
    (taskId: number, fields: Partial<TaskOut>) =>
      mutate(() => apiUpdateTask(taskId, fields)),
    [mutate],
  );

  const rescheduleTask = useCallback(
    (taskId: number, start: Date) =>
      mutate(() =>
        apiUpdateTask(taskId, { actual_start: start.toISOString().slice(0, 10) }),
      ),
    [mutate],
  );

  const removeTask = useCallback(
    (taskId: number) => mutate(() => apiDeleteTask(taskId)),
    [mutate],
  );

  return { schedule, loading, error, refresh, updateTask, rescheduleTask, removeTask };
}
