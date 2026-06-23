import { useState } from "react";
import { ViewMode } from "gantt-task-react";
import { GanttView } from "../components/GanttView";
import { TaskTable } from "../components/TaskTable";
import { useSchedule } from "../hooks/useSchedule";
import { useElementSize } from "../hooks/useElementSize";

export function ProjectPage({ projectId }: { projectId: number }) {
  const { schedule, loading, error, updateTask, rescheduleTask, removeTask } =
    useSchedule(projectId);
  const [view, setView] = useState<ViewMode>(ViewMode.Month);
  const [tab, setTab] = useState<"gantt" | "grid">("gantt");
  const [showList, setShowList] = useState<boolean>(
    () => localStorage.getItem("rise_show_task_list") !== "false",
  );
  const { ref: regionRef, height } = useElementSize<HTMLDivElement>();

  const toggleList = () =>
    setShowList((v) => {
      localStorage.setItem("rise_show_task_list", String(!v));
      return !v;
    });

  if (loading && !schedule) return <p className="muted">Loading…</p>;
  if (!schedule) return <p className="muted">No schedule.</p>;

  const { project, tasks, dependencies } = schedule;
  const criticalCount = tasks.filter((t) => t.is_critical).length;

  return (
    <div className="project-page">
      <div className="page-head">
        <h2>{project.name}</h2>
        <div className="meta">
          <span>{project.deal_type}</span>
          <span>{project.units} units</span>
          <span>{project.stage}</span>
          <span>
            {project.planned_start} → {project.planned_finish}
          </span>
        </div>
      </div>

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
              <span className="legend-swatch critical" /> Critical ({criticalCount})
              <span className="legend-swatch normal" /> Float
              <span>◆ Milestone</span>
            </div>
            <button className="ghost-btn" onClick={toggleList}>
              {showList ? "Hide list" : "Show list"}
            </button>
            <div className="view-modes">
              {([ViewMode.Week, ViewMode.Month] as ViewMode[]).map((m) => (
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
            showTaskList={showList}
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
