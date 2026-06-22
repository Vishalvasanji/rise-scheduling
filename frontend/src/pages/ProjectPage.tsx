import { useState } from "react";
import { ViewMode } from "gantt-task-react";
import { GanttView } from "../components/GanttView";
import { TaskTable } from "../components/TaskTable";
import { useSchedule } from "../hooks/useSchedule";

export function ProjectPage({ projectId }: { projectId: number }) {
  const { schedule, loading, error, updateTask, rescheduleTask, removeTask } =
    useSchedule(projectId);
  const [view, setView] = useState<ViewMode>(ViewMode.Month);
  const [tab, setTab] = useState<"gantt" | "grid">("gantt");

  if (loading && !schedule) return <p className="muted">Loading…</p>;
  if (!schedule) return <p className="muted">No schedule.</p>;

  const { project, tasks, dependencies } = schedule;
  const criticalCount = tasks.filter((t) => t.is_critical).length;

  return (
    <div>
      <header className="project-header">
        <h2>{project.name}</h2>
        <div className="meta">
          <span>{project.deal_type}</span>
          <span>{project.units} units</span>
          <span>{project.stage}</span>
          <span>
            {project.planned_start} → {project.planned_finish}
          </span>
        </div>
        <div className="legend">
          <span className="legend-swatch critical" /> Critical path ({criticalCount})
          <span className="legend-swatch normal" /> Has float
          <span style={{ marginLeft: 8 }}>◆ Milestone</span>
        </div>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="toolbar">
        <div className="tabs">
          <button className={tab === "gantt" ? "active" : ""} onClick={() => setTab("gantt")}>
            Gantt
          </button>
          <button className={tab === "grid" ? "active" : ""} onClick={() => setTab("grid")}>
            Task grid
          </button>
        </div>
        {tab === "gantt" && (
          <div className="view-modes">
            {([ViewMode.Week, ViewMode.Month] as ViewMode[]).map((m) => (
              <button key={m} className={view === m ? "active" : ""} onClick={() => setView(m)}>
                {m}
              </button>
            ))}
          </div>
        )}
      </div>

      {tab === "gantt" ? (
        <div className="gantt-wrap">
          <GanttView
            tasks={tasks}
            dependencies={dependencies}
            onDateChange={rescheduleTask}
            viewMode={view}
          />
        </div>
      ) : (
        <TaskTable tasks={tasks} onUpdate={updateTask} onDelete={removeTask} />
      )}
    </div>
  );
}
