// Wraps gantt-task-react. Critical-path styling and milestone diamonds come
// straight from backend-computed fields (is_critical, is_milestone) — the
// frontend does NOT run CPM. Dragging a bar pins the task's actual_start and the
// backend recalculates the whole project.
//
// Per-row data the library doesn't forward (WBS, duration, predecessor/successor
// names, the adjustable name-column width) is supplied to the custom task-list
// and tooltip components through a React context, so those components keep a
// stable identity (column-resize doesn't remount them mid-drag).

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { CSSProperties, FC, MouseEvent as ReactMouseEvent } from "react";
import { Gantt, Task as GanttTask, ViewMode } from "gantt-task-react";
import "gantt-task-react/dist/index.css";
import type { DependencyOut, TaskOut } from "../types/schedule";
import { mmddyy, parseLocalDate } from "../lib/dates";

const CRITICAL = "#ff3b30";
const CRITICAL_SELECT = "#e0301f";
const NORMAL = "#0a84ff";
const NORMAL_SELECT = "#0060df";

// Task-list column widths (Task is adjustable; the rest are fixed).
const WBS_W = 56;
const FROM_W = 58;
const TO_W = 58;
const DAYS_W = 44;
const NAME_MIN = 90;
const NAME_MAX = 480;
const NAME_DEFAULT = 170;

interface Props {
  tasks: TaskOut[];
  dependencies: DependencyOut[];
  onDateChange: (taskId: number, start: Date) => void;
  viewMode?: ViewMode;
  /** Pixel height for the chart's internal scroll viewport (0 = auto-grow). */
  height?: number;
}

interface GanttMeta {
  wbs: Map<string, string>;
  days: Map<string, number>;
  pred: Map<string, string[]>;
  succ: Map<string, string[]>;
  nameWidth: number;
  onResizeStart: (e: ReactMouseEvent) => void;
}

const MetaContext = createContext<GanttMeta | null>(null);

const cellBase: CSSProperties = {
  display: "flex",
  alignItems: "center",
  padding: "0 8px",
  overflow: "hidden",
  whiteSpace: "nowrap",
  textOverflow: "ellipsis",
};

const resizeHandle: CSSProperties = {
  position: "absolute",
  top: 0,
  right: 0,
  height: "100%",
  width: 9,
  cursor: "col-resize",
  borderRight: "1px solid rgba(0,0,0,0.12)",
};

// ---- Custom task list (header + body) -----------------------------------

const GanttListHeader: FC<{ headerHeight: number; fontFamily: string; fontSize: string }> = ({
  headerHeight,
  fontFamily,
  fontSize,
}) => {
  const meta = useContext(MetaContext);
  const nameW = meta?.nameWidth ?? NAME_DEFAULT;
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        height: headerHeight,
        fontFamily,
        fontSize,
        fontWeight: 600,
        color: "#6e6e73",
        background: "#fbfbfd",
        borderBottom: "1px solid rgba(0,0,0,0.08)",
        boxSizing: "border-box",
      }}
    >
      <div style={{ ...cellBase, width: WBS_W }}>WBS</div>
      <div style={{ ...cellBase, width: nameW, position: "relative" }}>
        Task
        <span style={resizeHandle} onMouseDown={meta?.onResizeStart} />
      </div>
      <div style={{ ...cellBase, width: FROM_W }}>From</div>
      <div style={{ ...cellBase, width: TO_W }}>To</div>
      <div style={{ ...cellBase, width: DAYS_W }}>Days</div>
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
        const days = meta?.days.get(t.id) ?? 0;
        return (
          <div
            key={t.id}
            onClick={() => setSelectedTask(t.id)}
            style={{
              display: "flex",
              alignItems: "center",
              height: rowHeight,
              borderBottom: "1px solid rgba(0,0,0,0.05)",
              boxSizing: "border-box",
              cursor: "pointer",
            }}
          >
            <div style={{ ...cellBase, width: WBS_W, color: "#86868b" }}>
              {meta?.wbs.get(t.id) ?? ""}
            </div>
            <div style={{ ...cellBase, width: nameW }} title={t.name}>
              {t.name}
            </div>
            <div style={{ ...cellBase, width: FROM_W, color: "#6e6e73" }}>{mmddyy(t.start)}</div>
            <div style={{ ...cellBase, width: TO_W, color: "#6e6e73" }}>{mmddyy(t.end)}</div>
            <div style={{ ...cellBase, width: DAYS_W, color: "#6e6e73" }}>{days || ""}</div>
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
  const preds = meta?.pred.get(task.id) ?? [];
  const succs = meta?.succ.get(task.id) ?? [];
  const days = meta?.days.get(task.id) ?? 0;
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
      <div style={{ fontWeight: 600, marginBottom: 3 }}>{task.name}</div>
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
  tasks,
  dependencies,
  onDateChange,
  viewMode = ViewMode.Month,
  height = 0,
}: Props) {
  const [nameWidth, setNameWidth] = useState<number>(() => {
    const v = Number(localStorage.getItem("rise_gantt_name_w"));
    return v >= NAME_MIN && v <= NAME_MAX ? v : NAME_DEFAULT;
  });

  useEffect(() => {
    localStorage.setItem("rise_gantt_name_w", String(nameWidth));
  }, [nameWidth]);

  // Column-resize drag (window-level so it keeps tracking off the handle).
  const dragRef = useRef<{ startX: number; startW: number } | null>(null);
  const onResizeStart = useCallback(
    (e: ReactMouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragRef.current = { startX: e.clientX, startW: nameWidth };
      document.body.style.userSelect = "none";
    },
    [nameWidth],
  );
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragRef.current) return;
      const dw = e.clientX - dragRef.current.startX;
      setNameWidth(Math.min(NAME_MAX, Math.max(NAME_MIN, dragRef.current.startW + dw)));
    };
    const onUp = () => {
      if (dragRef.current) {
        dragRef.current = null;
        document.body.style.userSelect = "";
      }
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

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
        return {
          id: String(t.id),
          name: t.name,
          type: t.is_milestone ? "milestone" : "task",
          start,
          end,
          progress: Math.round(t.percent_complete),
          dependencies: predecessorsOf.get(t.id),
          isDisabled: false,
          styles: {
            backgroundColor: t.is_critical ? CRITICAL : NORMAL,
            backgroundSelectedColor: t.is_critical ? CRITICAL_SELECT : NORMAL_SELECT,
            progressColor: t.is_critical ? "#c4271d" : "#0060df",
            progressSelectedColor: "#003a99",
          },
        } as GanttTask;
      });
  }, [tasks, dependencies]);

  // Per-row metadata + dependency labels for the custom list and tooltip.
  const meta = useMemo<Omit<GanttMeta, "nameWidth" | "onResizeStart">>(() => {
    const nameById = new Map<string, string>();
    const wbs = new Map<string, string>();
    const days = new Map<string, number>();
    for (const t of tasks) {
      const id = String(t.id);
      nameById.set(id, t.name);
      wbs.set(id, t.wbs ?? "");
      days.set(id, t.is_milestone ? 0 : t.duration_days);
    }
    const pred = new Map<string, string[]>();
    const succ = new Map<string, string[]>();
    for (const d of dependencies) {
      const p = String(d.predecessor_id);
      const s = String(d.successor_id);
      (pred.get(s) ?? pred.set(s, []).get(s)!).push(nameById.get(p) ?? p);
      (succ.get(p) ?? succ.set(p, []).get(p)!).push(nameById.get(s) ?? s);
    }
    return { wbs, days, pred, succ };
  }, [tasks, dependencies]);

  const metaValue = useMemo<GanttMeta>(
    () => ({ ...meta, nameWidth, onResizeStart }),
    [meta, nameWidth, onResizeStart],
  );

  if (ganttTasks.length === 0) {
    return <p className="muted">No scheduled tasks yet.</p>;
  }

  const listWidth = WBS_W + nameWidth + FROM_W + TO_W + DAYS_W;
  const columnWidth =
    viewMode === ViewMode.Month ? 200 : viewMode === ViewMode.Week ? 65 : 30;

  return (
    <MetaContext.Provider value={metaValue}>
      <Gantt
        tasks={ganttTasks}
        viewMode={viewMode}
        onDateChange={(task: GanttTask) => onDateChange(Number(task.id), task.start)}
        listCellWidth={`${listWidth}px`}
        columnWidth={columnWidth}
        ganttHeight={height > 0 ? Math.max(height - 72, 200) : undefined}
        rowHeight={38}
        headerHeight={42}
        barCornerRadius={4}
        fontSize="13px"
        TaskListHeader={GanttListHeader}
        TaskListTable={GanttListTable}
        TooltipContent={GanttTooltip}
      />
    </MetaContext.Provider>
  );
}
