// Wraps gantt-task-react. Critical-path styling and milestone diamonds come
// straight from backend-computed fields (is_critical, is_milestone) — the
// frontend does NOT run CPM. Dragging a bar pins the task's actual_start and the
// backend recalculates the whole project.
//
// Rows arrive pre-built by ProjectPage (WBS roll-up groups + leaf tasks, already
// filtered to the visible/expanded set). Group rows render as gantt-task-react
// "project" summary bars; leaf rows as task/milestone bars. Per-row data the
// library doesn't forward (WBS, duration, depth/group/collapsed, predecessor and
// successor names, the adjustable name-column width) is supplied to the custom
// task-list and tooltip components through a React context, so those components
// keep a stable identity (column-resize doesn't remount them mid-drag).

import { createContext, useContext, useMemo } from "react";
import type { FC, MouseEvent as ReactMouseEvent } from "react";
import { Gantt, Task as GanttTask, ViewMode } from "gantt-task-react";
import "gantt-task-react/dist/index.css";
import type { ChangeType, DependencyOut, TaskOut } from "../types/schedule";
import type { Row } from "../lib/rollup";
import { mmddyy, parseLocalDate } from "../lib/dates";
import {
  LeadCells,
  LeadHeader,
  bodyRowStyle,
  headerRowStyle,
  leadWidth,
  useSharedNameWidth,
  NAME_DEFAULT,
} from "./taskColumns";

const CRITICAL = "#ff3b30";
const CRITICAL_SELECT = "#e0301f";
const NORMAL = "#0a84ff";
const NORMAL_SELECT = "#0060df";
// Summary (roll-up) bars use a neutral slate so they read as structure, not work.
const SUMMARY = "#8a8a8e";
const SUMMARY_SELECT = "#6e6e73";
const SUMMARY_PROGRESS = "#6e6e73";

// Review-mode change coloring: green = added, amber = moved/modified.
const CHANGE_STYLE: Record<ChangeType, GanttTask["styles"]> = {
  new: {
    backgroundColor: "#34c759",
    backgroundSelectedColor: "#28a745",
    progressColor: "#1e9e4a",
    progressSelectedColor: "#17833c",
  },
  moved: {
    backgroundColor: "#ff9f0a",
    backgroundSelectedColor: "#e08e00",
    progressColor: "#cc7f00",
    progressSelectedColor: "#b36f00",
  },
  modified: {
    backgroundColor: "#ff9f0a",
    backgroundSelectedColor: "#e08e00",
    progressColor: "#cc7f00",
    progressSelectedColor: "#b36f00",
  },
  removed: {
    backgroundColor: "#c7c7cc",
    backgroundSelectedColor: "#aeaeb2",
    progressColor: "#aeaeb2",
    progressSelectedColor: "#8e8e93",
  },
};

interface RowInfo {
  wbs: string;
  days: number;
  depth: number;
  isGroup: boolean;
  collapsed: boolean;
}

interface Props {
  rows: Row[];
  tasks: TaskOut[];
  dependencies: DependencyOut[];
  collapsed: Set<string>;
  onToggle: (id: string) => void;
  onDateChange: (taskId: number, start: Date) => void;
  viewMode?: ViewMode;
  /** Pixel height for the chart's internal scroll viewport (0 = auto-grow). */
  height?: number;
  /** Review mode: task id -> change kind. Present => color bars + read-only. */
  changeStatus?: Map<number, ChangeType>;
}

interface GanttMeta {
  rowInfo: Map<string, RowInfo>;
  pred: Map<string, string[]>;
  succ: Map<string, string[]>;
  nameWidth: number;
  onResizeStart: (e: ReactMouseEvent) => void;
  onToggle: (id: string) => void;
}

const MetaContext = createContext<GanttMeta | null>(null);

// ---- Custom task list (header + body) -----------------------------------
// The five lead columns come from the shared `taskColumns` module so the Gantt
// list and the Task grid render them identically. The library injects these
// components and forwards only its own props, so per-row data and the adjustable
// name width arrive through MetaContext.

const GanttListHeader: FC<{ headerHeight: number; fontFamily: string; fontSize: string }> = ({
  headerHeight,
  fontFamily,
}) => {
  const meta = useContext(MetaContext);
  const nameW = meta?.nameWidth ?? NAME_DEFAULT;
  return (
    <div style={{ ...headerRowStyle, height: headerHeight, fontFamily }}>
      <LeadHeader nameWidth={nameW} onResizeStart={meta?.onResizeStart ?? (() => {})} />
    </div>
  );
};

const GanttListTable: FC<{
  rowHeight: number;
  fontFamily: string;
  fontSize: string;
  tasks: GanttTask[];
  setSelectedTask: (taskId: string) => void;
}> = ({ rowHeight, fontFamily, fontSize, tasks, setSelectedTask }) => {
  const meta = useContext(MetaContext);
  const nameW = meta?.nameWidth ?? NAME_DEFAULT;
  return (
    <div style={{ fontFamily, fontSize }}>
      {tasks.map((t) => {
        const info = meta?.rowInfo.get(t.id);
        const isGroup = info?.isGroup ?? false;
        return (
          <div
            key={t.id}
            onClick={() => (isGroup ? meta?.onToggle(t.id) : setSelectedTask(t.id))}
            style={{ ...bodyRowStyle, height: rowHeight, cursor: "pointer" }}
          >
            <LeadCells
              nameWidth={nameW}
              wbs={info?.wbs ?? ""}
              name={t.name}
              from={t.start}
              to={t.end}
              days={info?.days ?? 0}
              isMilestone={t.type === "milestone"}
              depth={info?.depth ?? 0}
              isGroup={isGroup}
              collapsed={info?.collapsed}
              onToggle={isGroup ? () => meta?.onToggle(t.id) : undefined}
            />
          </div>
        );
      })}
    </div>
  );
};

// ---- Custom hover tooltip (predecessor / successor) ----------------------

const GanttTooltip: FC<{ task: GanttTask; fontSize: string; fontFamily: string }> = ({
  task,
  fontSize,
  fontFamily,
}) => {
  const meta = useContext(MetaContext);
  const info = meta?.rowInfo.get(task.id);
  const preds = meta?.pred.get(task.id) ?? [];
  const succs = meta?.succ.get(task.id) ?? [];
  const days = info?.days ?? 0;
  return (
    <div
      style={{
        fontFamily,
        fontSize,
        background: "#fff",
        color: "#1d1d1f",
        borderRadius: 8,
        boxShadow: "0 8px 28px rgba(0,0,0,0.16)",
        padding: "9px 11px",
        maxWidth: 300,
        lineHeight: 1.45,
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 3 }}>
        {info?.isGroup ? `${info.wbs} · ` : ""}
        {task.name}
      </div>
      <div style={{ color: "#6e6e73" }}>
        {mmddyy(task.start)} → {mmddyy(task.end)}
        {days ? ` · ${days}d` : ""}
      </div>
      {preds.length > 0 && (
        <div style={{ marginTop: 5 }}>
          <span style={{ color: "#86868b" }}>Preceded by: </span>
          {preds.join(", ")}
        </div>
      )}
      {succs.length > 0 && (
        <div style={{ marginTop: 3 }}>
          <span style={{ color: "#86868b" }}>Followed by: </span>
          {succs.join(", ")}
        </div>
      )}
    </div>
  );
};

// ---- Main component ------------------------------------------------------

export function GanttView({
  rows,
  tasks,
  dependencies,
  collapsed,
  onToggle,
  onDateChange,
  viewMode = ViewMode.Month,
  height = 0,
  changeStatus,
}: Props) {
  const { nameWidth, onResizeStart } = useSharedNameWidth();
  const review = !!changeStatus;

  const ganttTasks = useMemo<GanttTask[]>(() => {
    // Predecessor arrows only between tasks that are currently visible.
    const visibleTaskIds = new Set(rows.filter((r) => r.kind === "task").map((r) => r.id));
    const predecessorsOf = new Map<string, string[]>();
    for (const d of dependencies) {
      const s = String(d.successor_id);
      const p = String(d.predecessor_id);
      if (!visibleTaskIds.has(s) || !visibleTaskIds.has(p)) continue;
      (predecessorsOf.get(s) ?? predecessorsOf.set(s, []).get(s)!).push(p);
    }

    const out: GanttTask[] = [];
    rows.forEach((r, i) => {
      if (r.kind === "group") {
        if (!r.start || !r.finish) return;
        out.push({
          id: r.id,
          name: r.name,
          type: "project",
          start: parseLocalDate(r.start),
          end: parseLocalDate(r.finish),
          progress: Math.round(r.percent),
          displayOrder: i + 1,
          isDisabled: true,
          hideChildren: collapsed.has(r.id),
          styles: {
            backgroundColor: r.isCritical ? CRITICAL : SUMMARY,
            backgroundSelectedColor: r.isCritical ? CRITICAL_SELECT : SUMMARY_SELECT,
            progressColor: r.isCritical ? "#c4271d" : SUMMARY_PROGRESS,
            progressSelectedColor: "#5a5a5e",
          },
        } as GanttTask);
      } else {
        const t = r.task;
        if (!t.planned_start || !t.planned_finish) return;
        const start = parseLocalDate(t.planned_start);
        const end = t.is_milestone ? start : parseLocalDate(t.planned_finish);
        const change = changeStatus?.get(t.id);
        out.push({
          id: String(t.id),
          name: t.name,
          type: t.is_milestone ? "milestone" : "task",
          start,
          end,
          progress: Math.round(t.percent_complete),
          dependencies: predecessorsOf.get(String(t.id)),
          displayOrder: i + 1,
          isDisabled: review, // review mode is read-only (no drag-to-reschedule)
          styles: change
            ? CHANGE_STYLE[change]
            : {
                backgroundColor: t.is_critical ? CRITICAL : NORMAL,
                backgroundSelectedColor: t.is_critical ? CRITICAL_SELECT : NORMAL_SELECT,
                progressColor: t.is_critical ? "#c4271d" : "#0060df",
                progressSelectedColor: "#003a99",
              },
        } as GanttTask);
      }
    });
    return out;
  }, [rows, dependencies, collapsed, changeStatus, review]);

  // Per-row metadata + dependency labels for the custom list and tooltip.
  const meta = useMemo<Omit<GanttMeta, "nameWidth" | "onResizeStart" | "onToggle">>(() => {
    const nameById = new Map<string, string>();
    for (const t of tasks) nameById.set(String(t.id), t.name);

    const rowInfo = new Map<string, RowInfo>();
    for (const r of rows) {
      if (r.kind === "group") {
        rowInfo.set(r.id, {
          wbs: r.code,
          days: r.days,
          depth: r.depth,
          isGroup: true,
          collapsed: collapsed.has(r.id),
        });
      } else {
        rowInfo.set(r.id, {
          wbs: r.code,
          days: r.task.is_milestone ? 0 : r.task.duration_days,
          depth: r.depth,
          isGroup: false,
          collapsed: false,
        });
      }
    }

    const pred = new Map<string, string[]>();
    const succ = new Map<string, string[]>();
    for (const d of dependencies) {
      const p = String(d.predecessor_id);
      const s = String(d.successor_id);
      (pred.get(s) ?? pred.set(s, []).get(s)!).push(nameById.get(p) ?? p);
      (succ.get(p) ?? succ.set(p, []).get(p)!).push(nameById.get(s) ?? s);
    }
    return { rowInfo, pred, succ };
  }, [rows, tasks, dependencies, collapsed]);

  const metaValue = useMemo<GanttMeta>(
    () => ({ ...meta, nameWidth, onResizeStart, onToggle }),
    [meta, nameWidth, onResizeStart, onToggle],
  );

  if (ganttTasks.length === 0) {
    return <p className="muted">No scheduled tasks yet.</p>;
  }

  const listWidth = leadWidth(nameWidth);
  const columnWidth =
    viewMode === ViewMode.Month ? 200 : viewMode === ViewMode.Week ? 65 : 30;

  return (
    <MetaContext.Provider value={metaValue}>
      <Gantt
        tasks={ganttTasks}
        viewMode={viewMode}
        onDateChange={(task: GanttTask) => {
          if (review) return; // proposed schedule is read-only
          if (!task.id.startsWith("g:")) onDateChange(Number(task.id), task.start);
        }}
        onExpanderClick={(task: GanttTask) => onToggle(task.id)}
        listCellWidth={`${listWidth}px`}
        columnWidth={columnWidth}
        ganttHeight={height > 0 ? Math.max(height - 72, 200) : undefined}
        rowHeight={38}
        headerHeight={42}
        barCornerRadius={4}
        fontFamily="var(--font)"
        fontSize="13px"
        TaskListHeader={GanttListHeader}
        TaskListTable={GanttListTable}
        TooltipContent={GanttTooltip}
      />
    </MetaContext.Provider>
  );
}
