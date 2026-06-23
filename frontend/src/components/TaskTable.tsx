// Read/edit task grid. Editing duration or % complete or status PATCHes the
// task; the backend recalculates and the parent refetches.

import { useState } from "react";
import type { TaskOut } from "../types/schedule";
import { mmddyy } from "../lib/dates";

interface Props {
  tasks: TaskOut[];
  onUpdate: (taskId: number, fields: Partial<TaskOut>) => void;
  onDelete: (taskId: number) => void;
}

export function TaskTable({ tasks, onUpdate, onDelete }: Props) {
  return (
    <table className="task-table">
      <thead>
        <tr>
          <th>WBS</th>
          <th>Task</th>
          <th>Dur</th>
          <th>Start</th>
          <th>Finish</th>
          <th>Float</th>
          <th>%</th>
          <th>Status</th>
          <th>Critical</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {tasks.map((t) => (
          <Row key={t.id} task={t} onUpdate={onUpdate} onDelete={onDelete} />
        ))}
      </tbody>
    </table>
  );
}

function Row({ task, onUpdate, onDelete }: { task: TaskOut } & Omit<Props, "tasks">) {
  const [pct, setPct] = useState(task.percent_complete);
  return (
    <tr className={task.is_critical ? "critical-row" : ""}>
      <td className="muted">{task.wbs}</td>
      <td>
        {task.is_milestone ? "◆ " : ""}
        {task.name}
      </td>
      <td>{task.is_milestone ? "—" : task.duration_days}</td>
      <td>{task.planned_start ? mmddyy(task.planned_start) : "—"}</td>
      <td>{task.planned_finish ? mmddyy(task.planned_finish) : "—"}</td>
      <td className={(task.total_float ?? 0) < 0 ? "negative" : ""}>
        {task.total_float ?? "—"}
      </td>
      <td>
        <input
          type="number"
          min={0}
          max={100}
          value={pct}
          onChange={(e) => setPct(Number(e.target.value))}
          onBlur={() => {
            if (pct !== task.percent_complete)
              onUpdate(task.id, { percent_complete: pct });
          }}
          style={{ width: 52 }}
        />
      </td>
      <td>
        <select
          value={task.status}
          onChange={(e) =>
            onUpdate(task.id, { status: e.target.value as TaskOut["status"] })
          }
        >
          <option value="not_started">not started</option>
          <option value="in_progress">in progress</option>
          <option value="complete">complete</option>
          <option value="blocked">blocked</option>
        </select>
      </td>
      <td>{task.is_critical ? "●" : ""}</td>
      <td>
        <button className="link-danger" onClick={() => onDelete(task.id)}>
          delete
        </button>
      </td>
    </tr>
  );
}
