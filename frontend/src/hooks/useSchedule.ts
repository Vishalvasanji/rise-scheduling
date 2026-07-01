// Fetches a project's schedule and exposes mutations. Edits carry the task's
// version for optimistic locking: if someone else changed the task first, the
// server returns 409 and we surface a confirm-to-overwrite dialog (who changed
// it). The schedule also live-refreshes (~10s + on focus) so collaborators see
// each other's edits — without clobbering a field that's being typed.

import { useCallback, useEffect, useRef, useState } from "react";
import {
  deleteTask as apiDeleteTask,
  getSchedule,
  updateTask as apiUpdateTask,
  type TaskEdit,
} from "../api/schedule";
import { ApiError } from "../api/client";
import type { ScheduleOut, TaskOut } from "../types/schedule";

const POLL_MS = 10000;

export interface ScheduleConflict {
  taskName: string;
  updatedBy: string | null;
  updatedAt: string | null;
  apply: () => Promise<void>; // overwrite (force) the pending edit
}

function isEditingField(): boolean {
  const el = document.activeElement;
  if (!el) return false;
  const tag = el.tagName;
  return tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA";
}

export function useSchedule(projectId: number | null) {
  const [schedule, setSchedule] = useState<ScheduleOut | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conflict, setConflict] = useState<ScheduleConflict | null>(null);
  // Keep a ref of the latest schedule so callbacks can read versions without
  // being re-created on every fetch.
  const scheduleRef = useRef<ScheduleOut | null>(null);
  scheduleRef.current = schedule;

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

  // Initial load + live polling. The poll is silent (no spinner) and skips
  // applying while a grid field is focused, so it can't reset an in-progress edit.
  useEffect(() => {
    void refresh();
    const poll = async () => {
      if (projectId == null || isEditingField()) return;
      try {
        const fresh = await getSchedule(projectId);
        setSchedule((prev) =>
          prev && JSON.stringify(prev) === JSON.stringify(fresh) ? prev : fresh,
        );
      } catch {
        /* transient — keep current state */
      }
    };
    const id = window.setInterval(() => void poll(), POLL_MS);
    const onFocus = () => void poll();
    window.addEventListener("focus", onFocus);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("focus", onFocus);
    };
  }, [projectId, refresh]);

  const reportError = useCallback((e: unknown) => {
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
  }, []);

  // Run a task edit with optimistic locking. Resolves `true` if the edit was applied,
  // `false` if it failed or hit a conflict — so callers (e.g. the Gantt) can revert.
  // On a 409 we stage a conflict the UI resolves (overwrite → retry with force).
  const runEdit = useCallback(
    async (taskId: number, fields: TaskEdit): Promise<boolean> => {
      const task = scheduleRef.current?.tasks.find((t) => t.id === taskId);
      const send = (force: boolean) =>
        apiUpdateTask(taskId, { ...fields, expected_version: task?.version, force });
      try {
        await send(false);
        setError(null);
        await refresh();
        return true;
      } catch (e) {
        if (
          e instanceof ApiError &&
          e.status === 409 &&
          (e.body as Record<string, unknown> | undefined)?.error === "version_conflict"
        ) {
          const b = e.body as Record<string, unknown>;
          setConflict({
            taskName: task?.name ?? "this task",
            updatedBy: (b.updated_by as string) ?? null,
            updatedAt: (b.updated_at as string) ?? null,
            apply: async () => {
              setConflict(null);
              try {
                await send(true);
                setError(null);
              } catch (err) {
                reportError(err);
              } finally {
                await refresh();
              }
            },
          });
          await refresh(); // show the latest while the user decides
        } else {
          reportError(e);
          await refresh();
        }
        return false;
      }
    },
    [refresh, reportError],
  );

  const updateTask = useCallback(
    (taskId: number, fields: Partial<TaskOut>) => runEdit(taskId, fields),
    [runEdit],
  );

  const removeTask = useCallback(
    async (taskId: number) => {
      try {
        await apiDeleteTask(taskId);
        setError(null);
      } catch (e) {
        reportError(e);
      } finally {
        await refresh();
      }
    },
    [refresh, reportError],
  );

  const dismissConflict = useCallback(() => {
    setConflict(null);
    void refresh();
  }, [refresh]);

  return {
    schedule,
    loading,
    error,
    conflict,
    dismissConflict,
    refresh,
    updateTask,
    removeTask,
  };
}
