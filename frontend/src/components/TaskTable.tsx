// Read/edit task grid. The first five columns (WBS · Task · From · To · Days) are
// the shared lead block rendered identically to the Gantt list; everything after
// them is grid-only (Trade · Float · % · Critical · delete). Every editable field
// (name, Days, Trade, %) edits inline on click via CellInput — no dropdowns. WBS,
// the planned dates, Float and Critical are engine-computed and read-only. WBS
// roll-up group rows are bold, collapsible, and read-only.

import type { CSSProperties } from "react";
import type { TaskOut } from "../types/schedule";
import type { GroupRow, Row, TaskRow } from "../lib/rollup";
import {
  CellInput,
  LeadCells,
  LeadHeader,
  bodyRowStyle,
  cellBase,
  cellCenter,
  headerRowStyle,
  leadWidth,
  useSharedNameWidth,
} from "./taskColumns";

interface Props {
  rows: Row[];
  collapsed: Set<string>;
  onToggle: (id: string) => void;
  onUpdate: (taskId: number, fields: Partial<TaskOut>) => void;
  onDelete: (taskId: number) => void;
}

// Trailing (grid-only) column widths.
const TRADE_W = 130;
const FLOAT_W = 64;
const PCT_W = 64;
const CRIT_W = 64;
const DEL_W = 72;

const trailingWidth = TRADE_W + FLOAT_W + PCT_W + CRIT_W + DEL_W;

export function TaskTable({ rows, collapsed, onToggle, onUpdate, onDelete }: Props) {
  const { nameWidth, onResizeStart } = useSharedNameWidth();
  const minWidth = leadWidth(nameWidth) + trailingWidth;

  return (
    <div className="task-grid" style={{ minWidth, fontSize: "13px" }}>
      <div className="task-grid__header" style={headerRowStyle}>
        <LeadHeader nameWidth={nameWidth} onResizeStart={onResizeStart} />
        <div style={{ ...cellBase, width: TRADE_W }}>Trade</div>
        <div style={{ ...cellCenter, width: FLOAT_W }}>Float</div>
        <div style={{ ...cellCenter, width: PCT_W }}>%</div>
        <div style={{ ...cellCenter, width: CRIT_W }}>Critical</div>
        <div style={{ ...cellBase, width: DEL_W }} />
      </div>
      {rows.map((r) =>
        r.kind === "group" ? (
          <GroupLine
            key={r.id}
            row={r}
            nameWidth={nameWidth}
            collapsed={collapsed.has(r.id)}
            onToggle={() => onToggle(r.id)}
          />
        ) : (
          <Line key={r.id} row={r} nameWidth={nameWidth} onUpdate={onUpdate} onDelete={onDelete} />
        ),
      )}
    </div>
  );
}

function GroupLine({
  row,
  nameWidth,
  collapsed,
  onToggle,
}: {
  row: GroupRow;
  nameWidth: number;
  collapsed: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="task-grid__row task-grid__group" style={bodyRowStyle}>
      <LeadCells
        nameWidth={nameWidth}
        wbs={row.code}
        name={row.name}
        from={row.start}
        to={row.finish}
        days={row.days}
        isMilestone={false}
        depth={row.depth}
        isGroup
        collapsed={collapsed}
        onToggle={onToggle}
      />
      <div style={{ ...cellBase, width: TRADE_W }} />
      <div style={{ ...cellCenter, width: FLOAT_W, color: "var(--text-3)" }}>—</div>
      <div style={{ ...cellCenter, width: PCT_W, color: "var(--text-2)" }}>{Math.round(row.percent)}</div>
      <div style={{ ...cellCenter, width: CRIT_W, color: "var(--red)" }}>
        {row.isCritical ? "●" : ""}
      </div>
      <div style={{ ...cellBase, width: DEL_W }} />
    </div>
  );
}

function Line({
  row,
  nameWidth,
  onUpdate,
  onDelete,
}: {
  row: TaskRow;
  nameWidth: number;
  onUpdate: Props["onUpdate"];
  onDelete: Props["onDelete"];
}) {
  const task = row.task;
  const float = task.total_float ?? null;
  const floatStyle: CSSProperties = {
    ...cellCenter,
    width: FLOAT_W,
    color: float !== null && float < 0 ? "var(--red)" : "var(--text-2)",
    fontWeight: float !== null && float < 0 ? 600 : 400,
  };

  return (
    <div className="task-grid__row" style={bodyRowStyle}>
      <LeadCells
        nameWidth={nameWidth}
        wbs={row.code}
        name={task.name}
        from={task.planned_start}
        to={task.planned_finish}
        days={task.duration_days}
        isMilestone={task.is_milestone}
        depth={row.depth}
        onCommitName={(v) => {
          if (v) onUpdate(task.id, { name: v });
        }}
        onCommitDays={(v) => {
          const n = Number(v);
          if (Number.isFinite(n) && n >= 0) onUpdate(task.id, { duration_days: Math.round(n) });
        }}
      />
      <div style={{ ...cellBase, width: TRADE_W, padding: 0 }}>
        <CellInput
          value={task.trade ?? ""}
          placeholder="—"
          ariaLabel="Trade"
          onCommit={(v) => onUpdate(task.id, { trade: v || null })}
        />
      </div>
      <div style={floatStyle}>{float ?? "—"}</div>
      <div style={{ ...cellCenter, width: PCT_W, padding: 0 }}>
        <CellInput
          value={String(task.percent_complete)}
          type="number"
          min={0}
          max={100}
          align="center"
          ariaLabel="Percent complete"
          onCommit={(v) => {
            const n = Number(v);
            if (Number.isFinite(n) && n >= 0 && n <= 100) onUpdate(task.id, { percent_complete: n });
          }}
        />
      </div>
      <div style={{ ...cellCenter, width: CRIT_W, color: "var(--red)" }}>
        {task.is_critical ? "●" : ""}
      </div>
      <div style={{ ...cellBase, width: DEL_W }}>
        <button className="link-danger" onClick={() => onDelete(task.id)}>
          delete
        </button>
      </div>
    </div>
  );
}
