import { useCallback, useEffect, useMemo, useState } from "react";
import { ViewMode } from "gantt-task-react";
import { GanttView } from "../components/GanttView";
import { TaskTable } from "../components/TaskTable";
import { ProposalReview } from "../components/ProposalReview";
import { useSchedule } from "../hooks/useSchedule";
import { useProposal } from "../hooks/useProposal";
import { useElementSize } from "../hooks/useElementSize";
import { buildRows, visibleRows } from "../lib/rollup";
import { addDaysISO, mmddyy, toISODate } from "../lib/dates";
import type { ChangeType, TaskOut } from "../types/schedule";

const VIEW_MODES: ViewMode[] = [ViewMode.Day, ViewMode.Week, ViewMode.Month];

// Time-window presets the field uses to focus the schedule (a 2-week "lookahead"
// and a today view), alongside the full schedule.
type ScheduleRange = "all" | "today" | "2week";
const RANGES: { key: ScheduleRange; label: string }[] = [
  { key: "all", label: "All" },
  { key: "today", label: "Today" },
  { key: "2week", label: "2-Week" },
];

// A task is "in" a window if its planned span overlaps it (so work that started
// earlier but is still running shows up).
function overlaps(t: TaskOut, startIso: string, endIso: string): boolean {
  if (!t.planned_start || !t.planned_finish) return false;
  return t.planned_start <= endIso && t.planned_finish >= startIso;
}

export function ProjectPage({
  projectId,
  tab,
}: {
  projectId: number;
  tab: "gantt" | "grid";
}) {
  const { schedule, loading, error, refresh, updateTask, rescheduleTask, removeTask } =
    useSchedule(projectId);
  const { proposal, busy, apply, discard, undoLast } = useProposal(projectId, refresh);
  const [view, setView] = useState<ViewMode>(ViewMode.Month);
  const [range, setRange] = useState<ScheduleRange>("all");
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [reviewing, setReviewing] = useState(false);
  const { ref: regionRef, height } = useElementSize<HTMLDivElement>();

  // Picking a window also drops to a readable zoom; the user can still re-zoom.
  const selectRange = useCallback((r: ScheduleRange) => {
    setRange(r);
    if (r === "today") setView(ViewMode.Day);
    else if (r === "2week") setView(ViewMode.Week);
  }, []);

  const todayIso = useMemo(() => toISODate(new Date()), []);
  const activeWindow = useMemo(() => {
    if (range === "today") return { start: todayIso, end: todayIso };
    if (range === "2week") return { start: todayIso, end: addDaysISO(todayIso, 14) };
    return null;
  }, [range, todayIso]);

  // Leaving review whenever the proposal is gone (applied/discarded/replaced).
  useEffect(() => {
    if (!proposal) setReviewing(false);
  }, [proposal]);

  const toggle = useCallback((id: string) => {
    setCollapsed((cur) => {
      const next = new Set(cur);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }, []);

  const review = reviewing && !!proposal;
  // In review mode the Gantt/grid render the *proposed* schedule; otherwise the
  // live one.
  const source = review && proposal ? proposal.schedule : schedule;
  const tasks = source?.tasks;
  const labels = schedule?.project.wbs_labels;
  // The time-window filter applies to the Schedule (Gantt) view only.
  const viewTasks = useMemo(() => {
    if (!tasks) return tasks;
    if (tab !== "gantt" || !activeWindow) return tasks;
    return tasks.filter((t) => overlaps(t, activeWindow.start, activeWindow.end));
  }, [tasks, tab, activeWindow]);
  const rows = useMemo(
    () => (viewTasks ? buildRows(viewTasks, labels) : []),
    [viewTasks, labels],
  );
  const shown = useMemo(() => visibleRows(rows, collapsed), [rows, collapsed]);
  const groupIds = useMemo(
    () => rows.filter((r) => r.kind === "group").map((r) => r.id),
    [rows],
  );
  // task id -> kind of change, for review-mode coloring (removed tasks aren't in
  // the proposed schedule, so they only appear in the diff panel).
  const changeStatus = useMemo(() => {
    const m = new Map<number, ChangeType>();
    if (review && proposal) {
      for (const c of proposal.changes) {
        if (c.change_type !== "removed") m.set(c.task_id, c.change_type);
      }
    }
    return m;
  }, [review, proposal]);
  // Distinct trades already in use, for the Trade typeahead.
  const trades = useMemo(
    () =>
      Array.from(
        new Set((tasks ?? []).map((t) => t.trade?.trim()).filter((t): t is string => !!t)),
      ).sort((a, b) => a.localeCompare(b)),
    [tasks],
  );
  const allCollapsed = groupIds.length > 0 && groupIds.every((id) => collapsed.has(id));
  const expandAll = useCallback(() => setCollapsed(new Set()), []);
  const collapseAll = useCallback(() => setCollapsed(new Set(groupIds)), [groupIds]);

  if (loading && !schedule) return <p className="muted">Loading…</p>;
  if (!schedule || !source) return <p className="muted">No schedule.</p>;

  const dependencies = source.dependencies;
  const criticalCount = (viewTasks ?? source.tasks).filter((t) => t.is_critical).length;
  const hasGroups = groupIds.length > 0;
  const windowLabel = activeWindow
    ? range === "today"
      ? mmddyy(activeWindow.start)
      : `${mmddyy(activeWindow.start)} – ${mmddyy(activeWindow.end)}`
    : null;

  return (
    <div className="project-page">
      {error && <div className="error-banner">{error}</div>}

      {proposal && (
        <ProposalReview
          proposal={proposal}
          reviewing={review}
          busy={busy}
          liveFinish={schedule.project.planned_finish}
          onToggleReview={() => setReviewing((v) => !v)}
          onApply={apply}
          onDiscard={discard}
          onUndoLast={undoLast}
        />
      )}

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
                {review ? (
                  <>
                    <span className="lg-new">New</span>
                    <span className="lg-moved">Moved</span>
                  </>
                ) : (
                  <span className="lg-critical">Critical ({criticalCount})</span>
                )}
                <span className="lg-float">Float</span>
                <span className="lg-ms">◆ Milestone</span>
              </div>
              <div className="range-control">
                {windowLabel && <span className="range-caption">{windowLabel}</span>}
                <div className="range-modes">
                  {RANGES.map((r) => (
                    <button
                      key={r.key}
                      className={range === r.key ? "active" : ""}
                      onClick={() => selectRange(r.key)}
                    >
                      {r.label}
                    </button>
                  ))}
                </div>
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
            tasks={source.tasks}
            dependencies={dependencies}
            collapsed={collapsed}
            onToggle={toggle}
            onDateChange={rescheduleTask}
            viewMode={view}
            height={height}
            changeStatus={review ? changeStatus : undefined}
            emptyLabel={
              activeWindow ? "No tasks scheduled in this window." : "No scheduled tasks yet."
            }
          />
        ) : (
          <div className="table-scroll">
            <TaskTable
              rows={shown}
              trades={trades}
              collapsed={collapsed}
              onToggle={toggle}
              onUpdate={updateTask}
              onDelete={removeTask}
              changeStatus={review ? changeStatus : undefined}
            />
          </div>
        )}
      </div>
    </div>
  );
}
