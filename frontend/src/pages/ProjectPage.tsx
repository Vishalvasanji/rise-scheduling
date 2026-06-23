import { useState } from "react";
import { ViewMode } from "gantt-task-react";
import { GanttView } from "../components/GanttView";
import { TaskTable } from "../components/TaskTable";
import { useSchedule } from "../hooks/useSchedule";
import { useElementSize } from "../hooks/useElementSize";

const VIEW_MODES: ViewMode[] = [ViewMode.Day, ViewMode.Week, ViewMode.Month];

export function ProjectPage({ projectId }: { projectId: number }) {
  const { schedule, loading, error, updateTask, rescheduleTask, removeTask } =
    useSchedule(projectId);
  const [view, setView] = useState<ViewMode>(ViewMode.Month);
  const [tab, setTab] = useState<"gantt" | "grid">("gantt");
  const { ref: regionRef, height } = useElementSize<HTMLDivElement>();

  if (loading && !schedule) return <p className="muted">Loading…</p>;
  if (!schedule) return <p className="muted">No schedule.</p>;

  const { tasks, dependencies } = schedule;
  const criticalCount = tasks.filter((t) => t.is_critical).length;

  return (
    <div className="project-page">
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

      <div className="schedule-region" ref={regionRef}>
        {tab === "gantt" ? (
          <GanttView
            tasks={tasks}
            dependencies={dependencies}
            onDateChange={rescheduleTask}
            viewMode={view}
            height={height}
          />
        ) : (
          <div className="table-scroll">
            <TaskTable tasks={tasks} onUpdate={updateTask} onDelete={removeTask} />
          </div>
        )}
      </div>
    </div>
  );
}
