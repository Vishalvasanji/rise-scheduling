// Wraps gantt-task-react. Critical-path styling and milestone diamonds come
// straight from backend-computed fields (is_critical, is_milestone) — the
// frontend does NOT run CPM. Dragging a bar pins the task's actual_start and the
// backend recalculates the whole project.

import { useMemo } from "react";
import {
  Gantt,
  Task as GanttTask,
  ViewMode,
} from "gantt-task-react";
import "gantt-task-react/dist/index.css";
import type { DependencyOut, TaskOut } from "../types/schedule";

const CRITICAL = "#ff3b30";
const CRITICAL_SELECT = "#e0301f";
const NORMAL = "#0a84ff";
const NORMAL_SELECT = "#0060df";

interface Props {
  tasks: TaskOut[];
  dependencies: DependencyOut[];
  onDateChange: (taskId: number, start: Date) => void;
  viewMode?: ViewMode;
}

// Parse a YYYY-MM-DD string as a LOCAL calendar date. `new Date("2026-06-22")`
// is parsed as UTC midnight, which renders as the previous day in negative-UTC
// timezones — an off-by-one on the Gantt. Building from parts avoids that.
function parseLocalDate(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function GanttView({
  tasks,
  dependencies,
  onDateChange,
  viewMode = ViewMode.Month,
}: Props) {
  const ganttTasks = useMemo<GanttTask[]>(() => {
    const predecessorsOf = new Map<number, string[]>();
    for (const d of dependencies) {
      const list = predecessorsOf.get(d.successor_id) ?? [];
      list.push(String(d.predecessor_id));
      predecessorsOf.set(d.successor_id, list);
    }

    return tasks
      .filter((t) => t.planned_start && t.planned_finish)
      .map((t) => {
        const start = parseLocalDate(t.planned_start!);
        // planned_finish is the last working day (inclusive); a milestone is a point.
        const end = t.is_milestone ? start : parseLocalDate(t.planned_finish!);
        const barColor = t.is_critical ? CRITICAL : NORMAL;
        const barSelect = t.is_critical ? CRITICAL_SELECT : NORMAL_SELECT;
        return {
          id: String(t.id),
          name: `${t.wbs ? t.wbs + " " : ""}${t.name}`,
          type: t.is_milestone ? "milestone" : "task",
          start,
          end,
          progress: Math.round(t.percent_complete),
          dependencies: predecessorsOf.get(t.id),
          isDisabled: false,
          styles: {
            backgroundColor: barColor,
            backgroundSelectedColor: barSelect,
            progressColor: t.is_critical ? "#c4271d" : "#0060df",
            progressSelectedColor: "#003a99",
          },
        } as GanttTask;
      });
  }, [tasks, dependencies]);

  if (ganttTasks.length === 0) {
    return <p className="muted">No scheduled tasks yet.</p>;
  }

  return (
    <Gantt
      tasks={ganttTasks}
      viewMode={viewMode}
      onDateChange={(task: GanttTask) => onDateChange(Number(task.id), task.start)}
      listCellWidth="260px"
      columnWidth={viewMode === ViewMode.Month ? 200 : 65}
    />
  );
}
