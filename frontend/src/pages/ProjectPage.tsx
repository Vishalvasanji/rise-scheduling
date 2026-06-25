import { useCallback, useMemo, useState } from "react";
import { ViewMode } from "gantt-task-react";
import { GanttView } from "../components/GanttView";
import { TaskTable } from "../components/TaskTable";
import { useSchedule } from "../hooks/useSchedule";
import { useElementSize } from "../hooks/useElementSize";
import { buildRows, visibleRows } from "../lib/rollup";

const VIEW_MODES: ViewMode[] = [ViewMode.Day, ViewMode.Week, ViewMode.Month];

export function ProjectPage({
  projectId,
  tab,
}: {
  projectId: number;
  tab: "gantt" | "grid";
}) {
  const { schedule, loading, error, updateTask, rescheduleTask, removeTask } =
    useSchedule(projectId);
  const [view, setView] = useState<ViewMode>(ViewMode.Month);
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const { ref: regionRef, height } = useElementSize<HTMLDivElement>();

  const toggle = useCallback((id: string) => {
    setCollapsed((cur) => {
      const next = new Set(cur);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }, []);

  const tasks = schedule?.tasks;
  const rows = useMemo(() => (tasks ? buildRows(tasks) : []), [tasks]);
  const shown = useMemo(() => visibleRows(rows, collapsed), [rows, collapsed]);
  const groupIds = useMemo(
    () => rows.filter((r) => r.kind === "group").map((r) => r.id),
    [rows],
  );
  const allCollapsed = groupIds.length > 0 && groupIds.every((id) => collapsed.has(id));
  const expandAll = useCallback(() => setCollapsed(new Set()), []);
  const collapseAll = useCallback(() => setCollapsed(new Set(groupIds)), [groupIds]);

  if (loading && !schedule) return <p className="muted">Loading…</p>;
  if (!schedule) return <p className="muted">No schedule.</p>;

  const { dependencies } = schedule;
  const criticalCount = schedule.tasks.filter((t) => t.is_critical).length;
  const hasGroups = groupIds.length > 0;

  return (
    <div className="project-page">
      {error && <div className="error-banner">{error}</div>}

      {(tab === "gantt" || hasGroups) && (
        <div className="toolbar">
          {hasGroups ? (
            <div className="rollup-controls">
              <button onClick={expandAll} disabled={collapsed.size === 0}>
                Expand all
              </button>
              <button onClick={collapseAll} disabled={allCollapsed}>
                Collapse all
              </button>
            </div>
          ) : (
            <span />
          )}
          {tab === "gantt" && (
            <div className="toolbar__right">
              <div className="legend">
                <span className="lg-critical">Critical ({criticalCount})</span>
                <span className="lg-float">Float</span>
                <span className="lg-ms">◆ Milestone</span>
              </div>
              <div className="view-modes">
                {VIEW_MODES.map((m) => (
                  <button key={m} className={view === m ? "active" : ""} onClick={() => setView(m)}>
                    {m}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="schedule-region" ref={regionRef}>
        {tab === "gantt" ? (
          <GanttView
            rows={shown}
            tasks={schedule.tasks}
            dependencies={dependencies}
            collapsed={collapsed}
            onToggle={toggle}
            onDateChange={rescheduleTask}
            viewMode={view}
            height={height}
          />
        ) : (
          <div className="table-scroll">
            <TaskTable
              rows={shown}
              collapsed={collapsed}
              onToggle={toggle}
              onUpdate={updateTask}
              onDelete={removeTask}
            />
          </div>
        )}
      </div>
    </div>
  );
}
