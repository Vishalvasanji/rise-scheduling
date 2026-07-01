import { useCallback, useEffect, useMemo, useState } from "react";
import { ViewMode } from "gantt-task-react";
import { GanttView } from "../components/GanttView";
import { TaskTable } from "../components/TaskTable";
import { ProposalReview } from "../components/ProposalReview";
import { ConflictDialog } from "../components/ConflictDialog";
import { ConfirmChangeDialog } from "../components/ConfirmChangeDialog";
import { useSchedule } from "../hooks/useSchedule";
import { useProposal } from "../hooks/useProposal";
import { useElementSize } from "../hooks/useElementSize";
import { buildRows, visibleRows } from "../lib/rollup";
import { addDaysISO, businessDays, mmddyy, startOfWeekISO, toISODate } from "../lib/dates";
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

// A change awaiting the user's confirmation before it's written.
interface PendingEdit {
  taskName: string;
  lines: string[];
  run: () => Promise<boolean>;
  resolve: (ok: boolean) => void;
}

// Fields that reschedule a task — these route through the confirm modal.
const DATE_DUR_FIELDS = [
  "actual_start",
  "actual_finish",
  "start_no_earlier_than",
  "duration_days",
] as const;

const day = (v: string | null | undefined) => (v ? mmddyy(v) : "—");

// Human-readable summary of a date/duration change, for the confirm modal.
function describeEdit(t: TaskOut, fields: Partial<TaskOut>): string[] {
  const lines: string[] = [];
  if ("start_no_earlier_than" in fields || "actual_start" in fields) {
    const nv = (fields.actual_start ?? fields.start_no_earlier_than) as string | null;
    lines.push(`Start ${day(t.planned_start)} → ${day(nv)}`);
  }
  if ("actual_finish" in fields) {
    lines.push(`Finish ${day(t.planned_finish)} → ${day(fields.actual_finish as string | null)}`);
  }
  if ("duration_days" in fields) {
    lines.push(`Duration ${t.duration_days} → ${fields.duration_days} days`);
  }
  return lines;
}

export function ProjectPage({
  projectId,
  tab,
}: {
  projectId: number;
  tab: "gantt" | "grid";
}) {
  const { schedule, loading, error, conflict, dismissConflict, refresh, updateTask, removeTask } =
    useSchedule(projectId);
  const { proposal, busy, apply, discard, undoLast } = useProposal(projectId, refresh);
  const [view, setView] = useState<ViewMode>(ViewMode.Month);
  const [range, setRange] = useState<ScheduleRange>("all");
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [reviewing, setReviewing] = useState(false);
  const [pending, setPending] = useState<PendingEdit | null>(null);
  const [pendingBusy, setPendingBusy] = useState(false);
  // Bumped when a grid date/duration edit is cancelled, to remount the grid so a
  // typed-but-unconfirmed value snaps back to the server value.
  const [gridNonce, setGridNonce] = useState(0);
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
    if (range === "2week") {
      // Two full weeks starting on the Sunday on/before today (Sun … second Sat).
      const start = startOfWeekISO(todayIso);
      return { start, end: addDaysISO(start, 13) };
    }
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
  // The time-window filter applies to both the Schedule (Gantt) and Tasks views.
  const viewTasks = useMemo(() => {
    if (!tasks || !activeWindow) return tasks;
    return tasks.filter((t) => overlaps(t, activeWindow.start, activeWindow.end));
  }, [tasks, activeWindow]);
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

  // Every date/duration change is confirmed before it's written. Non-date edits
  // (name, trade, %, status) apply immediately. Returns whether it was applied, so
  // the Gantt can revert the bar on cancel/failure.
  const requestEdit = (taskId: number, fields: Partial<TaskOut>): Promise<boolean> => {
    const t = source.tasks.find((x) => x.id === taskId);
    const touchesSchedule = Object.keys(fields).some((k) =>
      (DATE_DUR_FIELDS as readonly string[]).includes(k),
    );
    if (!t || !touchesSchedule) return updateTask(taskId, fields);
    const lines = describeEdit(t, fields);
    if (lines.length === 0) return Promise.resolve(true); // nothing actually changed
    return new Promise<boolean>((resolve) => {
      setPending({ taskName: t.name, lines, resolve, run: () => updateTask(taskId, fields) });
    });
  };

  const confirmPending = async () => {
    if (!pending) return;
    setPendingBusy(true);
    const ok = await pending.run();
    pending.resolve(ok);
    setPending(null);
    setPendingBusy(false);
  };

  const cancelPending = () => {
    if (!pending) return;
    pending.resolve(false); // Gantt reverts the bar; grid date cell reverts on its own
    setPending(null);
    setGridNonce((n) => n + 1); // remount the grid so a typed duration snaps back
  };

  // Dragging/resizing a Gantt bar reschedules: a not-yet-started task moves via the
  // planning constraint, a started task edits its actual start; the span sets duration.
  const handleGanttDateChange = (taskId: number, start: Date, end: Date): Promise<boolean> => {
    const t = source.tasks.find((x) => x.id === taskId);
    if (!t) return Promise.resolve(false);
    const newStart = toISODate(start);
    const fields: Partial<TaskOut> = {};
    if (newStart !== t.planned_start) {
      if (t.actual_start) fields.actual_start = newStart;
      else fields.start_no_earlier_than = newStart;
    }
    if (!t.is_milestone) {
      const newDur = businessDays(start, end);
      if (newDur > 0 && newDur !== t.duration_days) fields.duration_days = newDur;
    }
    if (Object.keys(fields).length === 0) return Promise.resolve(true); // no-op
    return requestEdit(taskId, fields);
  };

  // Grid edits route through the same confirm flow (date/duration) or apply directly.
  const handleGridUpdate = (taskId: number, fields: Partial<TaskOut>) => {
    void requestEdit(taskId, fields);
  };

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

      {conflict && (
        <ConflictDialog
          taskName={conflict.taskName}
          updatedBy={conflict.updatedBy}
          updatedAt={conflict.updatedAt}
          onConfirm={conflict.apply}
          onCancel={dismissConflict}
        />
      )}

      {pending && (
        <ConfirmChangeDialog
          taskName={pending.taskName}
          lines={pending.lines}
          busy={pendingBusy}
          onConfirm={confirmPending}
          onCancel={cancelPending}
        />
      )}

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
        <div className="toolbar__right">
          {tab === "gantt" && (
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
          )}
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
          {tab === "gantt" && (
            <div className="view-modes">
              {VIEW_MODES.map((m) => (
                <button key={m} className={view === m ? "active" : ""} onClick={() => setView(m)}>
                  {m}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="schedule-region" ref={regionRef}>
        {tab === "gantt" ? (
          <GanttView
            rows={shown}
            tasks={source.tasks}
            dependencies={dependencies}
            collapsed={collapsed}
            onToggle={toggle}
            onDateChange={handleGanttDateChange}
            viewMode={view}
            height={height}
            changeStatus={review ? changeStatus : undefined}
            emptyLabel={
              activeWindow ? "No tasks scheduled in this window." : "No scheduled tasks yet."
            }
          />
        ) : shown.length === 0 ? (
          <p className="muted">
            {activeWindow ? "No tasks scheduled in this window." : "No tasks yet."}
          </p>
        ) : (
          <div className="table-scroll">
            <TaskTable
              key={gridNonce}
              rows={shown}
              trades={trades}
              collapsed={collapsed}
              onToggle={toggle}
              onUpdate={handleGridUpdate}
              onDelete={removeTask}
              changeStatus={review ? changeStatus : undefined}
            />
          </div>
        )}
      </div>
    </div>
  );
}
