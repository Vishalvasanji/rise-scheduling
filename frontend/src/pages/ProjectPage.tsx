import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ViewMode } from "gantt-task-react";
import { GanttView } from "../components/GanttView";
import { TaskTable } from "../components/TaskTable";
import { ProposalReview } from "../components/ProposalReview";
import { ConflictDialog } from "../components/ConflictDialog";
import { BulkConflictDialog } from "../components/BulkConflictDialog";
import { useSchedule } from "../hooks/useSchedule";
import type { BulkConflict } from "../hooks/useSchedule";
import { useProposal } from "../hooks/useProposal";
import { useElementSize } from "../hooks/useElementSize";
import { buildRows, visibleRows } from "../lib/rollup";
import { addDaysISO, daysBetween, mmddyy, startOfWeekISO, toISODate } from "../lib/dates";
import type { BulkEdit } from "../api/schedule";
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

// Stable empty draft for when no edit session is active (so display overlays off).
const NO_DRAFT: Map<number, Partial<TaskOut>> = new Map();

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
  // Edit-session ("spreadsheet") state: the grid/Gantt list are read-only until
  // the pencil starts a session; edits stage into `draft` and Save pushes the
  // whole batch at once. Polling is paused while editing so nothing shifts under us.
  const [editMode, setEditMode] = useState(false);
  const [draft, setDraft] = useState<Map<number, Partial<TaskOut>>>(new Map());
  const baseVersions = useRef<Map<number, number>>(new Map());
  const [saving, setSaving] = useState(false);
  const [bulkConflicts, setBulkConflicts] = useState<BulkConflict[] | null>(null);
  // Post-save confirmation toast; auto-dismisses.
  const [savedToast, setSavedToast] = useState(false);
  const toastTimer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(toastTimer.current), []);

  const {
    schedule,
    loading,
    error,
    conflict,
    dismissConflict,
    refresh,
    removeTask,
    saveBulk,
  } = useSchedule(projectId, editMode);
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

  // ---- edit session -----------------------------------------------------------
  const setCell = useCallback((taskId: number, fields: Partial<TaskOut>) => {
    setDraft((prev) => {
      const next = new Map(prev);
      next.set(taskId, { ...(next.get(taskId) ?? {}), ...fields });
      return next;
    });
  }, []);

  const startEdit = useCallback(() => {
    const versions = new Map<number, number>();
    for (const t of schedule?.tasks ?? []) versions.set(t.id, t.version);
    baseVersions.current = versions;
    setDraft(new Map());
    setBulkConflicts(null);
    setEditMode(true);
  }, [schedule]);

  const cancelEdit = useCallback(() => {
    setDraft(new Map());
    setBulkConflicts(null);
    setEditMode(false);
  }, []);

  const draftCount = draft.size;

  const save = useCallback(
    async (force = false) => {
      const edits: BulkEdit[] = Array.from(draft.entries())
        .filter(([, f]) => Object.keys(f).length > 0)
        .map(([task_id, f]) => ({
          task_id,
          fields: { ...f, expected_version: baseVersions.current.get(task_id) },
        }));
      if (edits.length === 0) {
        setEditMode(false);
        return;
      }
      setSaving(true);
      const res = await saveBulk(edits, force);
      setSaving(false);
      if (res.ok) {
        setDraft(new Map());
        setBulkConflicts(null);
        setEditMode(false);
        setSavedToast(true);
        window.clearTimeout(toastTimer.current);
        toastTimer.current = window.setTimeout(() => setSavedToast(false), 2800);
      } else if (res.conflicts && res.conflicts.length > 0) {
        setBulkConflicts(res.conflicts);
      }
      // Other errors surface in the banner; stay in the session with the draft intact.
    },
    [draft, saveBulk],
  );

  // Delete applies immediately; drop any staged edits for that row so a later Save
  // doesn't reference a task that no longer exists.
  const handleDelete = useCallback(
    (taskId: number) => {
      setDraft((prev) => {
        if (!prev.has(taskId)) return prev;
        const next = new Map(prev);
        next.delete(taskId);
        return next;
      });
      baseVersions.current.delete(taskId);
      void removeTask(taskId);
    },
    [removeTask],
  );

  // Warn before a full page unload with unsaved edits.
  useEffect(() => {
    if (!editMode || draftCount === 0) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [editMode, draftCount]);

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
  // Toolbar reminders (independent of the active window / collapse): the next
  // upcoming milestone(s) and the project end date, both counted in calendar days
  // from today so the team always sees how much time is left.
  const nextMilestones = useMemo(() => {
    const upcoming = (source?.tasks ?? [])
      .filter((t) => t.is_milestone && t.status !== "complete")
      .map((t) => ({ t, date: t.planned_start ?? t.planned_finish }))
      .filter((m): m is { t: TaskOut; date: string } => !!m.date && m.date >= todayIso)
      .sort((a, b) => a.date.localeCompare(b.date));
    const nextDate = upcoming[0]?.date;
    return nextDate ? upcoming.filter((m) => m.date === nextDate) : [];
  }, [source, todayIso]);

  const allCollapsed = groupIds.length > 0 && groupIds.every((id) => collapsed.has(id));
  const expandAll = useCallback(() => setCollapsed(new Set()), []);
  const collapseAll = useCallback(() => setCollapsed(new Set(groupIds)), [groupIds]);

  if (loading && !schedule) return <p className="muted">Loading…</p>;
  if (!schedule || !source) return <p className="muted">No schedule.</p>;

  const dependencies = source.dependencies;
  const hasGroups = groupIds.length > 0;

  // "n days away/left" phrasing shared by both metrics (calendar days).
  const countLabel = (date: string, kind: "away" | "left"): string => {
    const n = daysBetween(todayIso, date);
    if (n === 0) return "today";
    if (n < 0) return `overdue by ${-n} day${n === -1 ? "" : "s"}`;
    return `${n} day${n === 1 ? "" : "s"} ${kind}`;
  };
  // Urgency accent: amber within a week, red once overdue.
  const urgency = (date: string): "" | "--soon" | "--over" => {
    const n = daysBetween(todayIso, date);
    if (n < 0) return "--over";
    if (n <= 7) return "--soon";
    return "";
  };
  const countClass = (date: string): string => {
    const u = urgency(date);
    return u ? `metric__count metric__count${u}` : "metric__count";
  };
  // The whole card glows amber/red so the reminder is impossible to miss.
  const cardClass = (date: string | null | undefined): string => {
    const u = date ? urgency(date) : "";
    return u ? `metric metric${u}` : "metric";
  };
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

      {bulkConflicts && (
        <BulkConflictDialog
          conflicts={bulkConflicts}
          busy={saving}
          onOverwrite={() => void save(true)}
          onCancel={() => setBulkConflicts(null)}
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

      {editMode && !review && (
        <div className="edit-mode-banner">
          <span className="edit-mode-banner__dot" />
          <span className="edit-mode-banner__text">
            {saving
              ? "Saving changes…"
              : "You're in edit mode — changes are staged. Click 💾 to save or ✕ to cancel."}
            {!saving && draftCount ? (
              <span className="edit-mode-banner__meta">{` · ${draftCount} unsaved change${
                draftCount === 1 ? "" : "s"
              }`}</span>
            ) : null}
          </span>
        </div>
      )}

      {saving && (
        <div className="status-pill status-pill--saving" role="status" aria-live="polite">
          <span className="spinner" aria-hidden />
          Saving changes…
        </div>
      )}
      {savedToast && !saving && (
        <div className="status-pill status-pill--saved" role="status" aria-live="polite">
          ✓ Changes saved
        </div>
      )}

      <div className="toolbar">
        <div className="toolbar__left">
        <div className="grid-tools">
          {hasGroups && (
            <>
              <button
                className="icon-btn"
                title="Expand all"
                aria-label="Expand all"
                onClick={expandAll}
                disabled={collapsed.size === 0}
              >
                ⇊
              </button>
              <button
                className="icon-btn"
                title="Collapse all"
                aria-label="Collapse all"
                onClick={collapseAll}
                disabled={allCollapsed}
              >
                ⇈
              </button>
            </>
          )}
          {!review &&
            (editMode ? (
              <>
                <button
                  className="icon-btn icon-btn--primary"
                  title={saving ? "Saving…" : "Save changes"}
                  aria-label="Save changes"
                  onClick={() => void save()}
                  disabled={saving || draftCount === 0}
                >
                  {saving ? <span className="spinner" aria-hidden /> : "💾"}
                </button>
                <button
                  className="icon-btn"
                  title="Cancel"
                  aria-label="Cancel editing"
                  onClick={cancelEdit}
                  disabled={saving}
                >
                  ✕
                </button>
              </>
            ) : (
              <button
                className="icon-btn"
                title="Edit"
                aria-label="Edit"
                onClick={startEdit}
              >
                ✏️
              </button>
            ))}
        </div>
          <div className="metrics">
            <div className={cardClass(nextMilestones[0]?.date)}>
              <span className="metric__label">
                Next Milestone{nextMilestones.length > 1 ? "s" : ""}
              </span>
              {nextMilestones.length === 0 ? (
                <span className="metric__value metric__value--muted">None upcoming</span>
              ) : (
                <span className="metric__value">
                  {nextMilestones
                    .map((m) => (m.t.building ? `${m.t.building}, ${m.t.name}` : m.t.name))
                    .join(" · ")}
                  , {mmddyy(nextMilestones[0].date)},{" "}
                  <span className={countClass(nextMilestones[0].date)}>
                    {countLabel(nextMilestones[0].date, "away")}
                  </span>
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="toolbar__right">
          {tab === "gantt" && review && (
            <div className="legend">
              <span className="lg-new">New</span>
              <span className="lg-moved">Moved</span>
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
            editMode={editMode && !review}
            draft={editMode && !review ? draft : NO_DRAFT}
            onCell={setCell}
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
              rows={shown}
              trades={trades}
              collapsed={collapsed}
              onToggle={toggle}
              editMode={editMode && !review}
              draft={editMode && !review ? draft : NO_DRAFT}
              onCell={setCell}
              onDelete={handleDelete}
              changeStatus={review ? changeStatus : undefined}
            />
          </div>
        )}
      </div>
    </div>
  );
}
