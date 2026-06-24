// Read/edit task grid. The first five columns (WBS · Task · From · To · Days) are
// the shared lead block rendered identically to the Gantt list; everything after
// them is grid-only (Float · % · Status · Critical · delete). Editing duration is
// not offered here — duration shows in the shared Days column; % / status PATCH the
// task and the backend recalculates.

import { useState } from "react";
import type { CSSProperties } from "react";
import type { TaskOut } from "../types/schedule";
import {
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
  tasks: TaskOut[];
  onUpdate: (taskId: number, fields: Partial<TaskOut>) => void;
  onDelete: (taskId: number) => void;
}

// Trailing (grid-only) column widths.
const FLOAT_W = 64;
const PCT_W = 72;
const STATUS_W = 132;
const CRIT_W = 64;
const DEL_W = 72;

const trailingWidth = FLOAT_W + PCT_W + STATUS_W + CRIT_W + DEL_W;

export function TaskTable({ tasks, onUpdate, onDelete }: Props) {
  const { nameWidth, onResizeStart } = useSharedNameWidth();
  const minWidth = leadWidth(nameWidth) + trailingWidth;

  return (
    <div className="task-grid" style={{ minWidth, fontSize: "13px" }}>
      <div className="task-grid__header" style={headerRowStyle}>
        <LeadHeader nameWidth={nameWidth} onResizeStart={onResizeStart} />
        <div style={{ ...cellCenter, width: FLOAT_W }}>Float</div>
        <div style={{ ...cellCenter, width: PCT_W }}>%</div>
        <div style={{ ...cellBase, width: STATUS_W }}>Status</div>
        <div style={{ ...cellCenter, width: CRIT_W }}>Critical</div>
        <div style={{ ...cellBase, width: DEL_W }} />
      </div>
      {tasks.map((t) => (
        <Row key={t.id} task={t} nameWidth={nameWidth} onUpdate={onUpdate} onDelete={onDelete} />
      ))}
    </div>
  );
}

function Row({
  task,
  nameWidth,
  onUpdate,
  onDelete,
}: { task: TaskOut; nameWidth: number } & Omit<Props, "tasks">) {
  const [pct, setPct] = useState(task.percent_complete);
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
        wbs={task.wbs ?? ""}
        name={task.name}
        from={task.planned_start ?? null}
        to={task.planned_finish ?? null}
        days={task.duration_days}
        isMilestone={task.is_milestone}
      />
      <div style={floatStyle}>{float ?? "—"}</div>
      <div style={{ ...cellCenter, width: PCT_W }}>
        <input
          type="number"
          min={0}
          max={100}
          value={pct}
          onChange={(e) => setPct(Number(e.target.value))}
          onBlur={() => {
            if (pct !== task.percent_complete) onUpdate(task.id, { percent_complete: pct });
          }}
          style={{ width: 52 }}
        />
      </div>
      <div style={{ ...cellBase, width: STATUS_W }}>
        <select
          value={task.status}
          onChange={(e) => onUpdate(task.id, { status: e.target.value as TaskOut["status"] })}
        >
          <option value="not_started">not started</option>
          <option value="in_progress">in progress</option>
          <option value="complete">complete</option>
          <option value="blocked">blocked</option>
        </select>
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
