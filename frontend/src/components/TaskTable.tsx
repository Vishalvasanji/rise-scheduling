// Read/edit task grid. The first five columns (WBS · Task · From · To · Days) are
// the shared lead block rendered identically to the Gantt list; everything after
// them is grid-only (Trade · Float · % · Critical · delete). Every editable field
// edits inline on click — name/% via text inputs, From/To via date pickers (which
// set the task's actuals and reschedule), Trade via a fuzzy-matching typeahead over
// trades already in use. WBS, Float and Critical are engine-computed / read-only.
// WBS roll-up group rows are bold, collapsible, and read-only.

import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import type { ChangeType, TaskOut } from "../types/schedule";
import type { GroupRow, Row, TaskRow } from "../lib/rollup";
import { businessDays } from "../lib/dates";
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
  trades: string[];
  collapsed: Set<string>;
  onToggle: (id: string) => void;
  onUpdate: (taskId: number, fields: Partial<TaskOut>) => void;
  onDelete: (taskId: number) => void;
  /** Review mode: task id -> change kind. Present => tint rows + read-only. */
  changeStatus?: Map<number, ChangeType>;
}

// Trailing (grid-only) column widths.
const TRADE_W = 140;
const FLOAT_W = 64;
const PCT_W = 64;
const CRIT_W = 64;
const DEL_W = 72;

const trailingWidth = TRADE_W + FLOAT_W + PCT_W + CRIT_W + DEL_W;

// "Trade" header / cell, placed right after Task via the LeadCells afterName slot.
const tradeHeader = <div style={{ ...cellBase, width: TRADE_W }}>Trade</div>;

export function TaskTable({
  rows,
  trades,
  collapsed,
  onToggle,
  onUpdate,
  onDelete,
  changeStatus,
}: Props) {
  const { nameWidth, onResizeStart } = useSharedNameWidth();
  const minWidth = leadWidth(nameWidth) + trailingWidth;
  const review = !!changeStatus;

  return (
    <div className="task-grid" style={{ minWidth, fontSize: "13px" }}>
      <div className="task-grid__header" style={headerRowStyle}>
        <LeadHeader nameWidth={nameWidth} onResizeStart={onResizeStart} afterName={tradeHeader} />
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
          <Line
            key={r.id}
            row={r}
            nameWidth={nameWidth}
            trades={trades}
            onUpdate={onUpdate}
            onDelete={onDelete}
            readOnly={review}
            change={changeStatus?.get(r.task.id)}
          />
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
        afterName={<div style={{ ...cellBase, width: TRADE_W }} />}
      />
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
  trades,
  onUpdate,
  onDelete,
  readOnly = false,
  change,
}: {
  row: TaskRow;
  nameWidth: number;
  trades: string[];
  onUpdate: Props["onUpdate"];
  onDelete: Props["onDelete"];
  readOnly?: boolean;
  change?: ChangeType;
}) {
  const task = row.task;
  // Days is a calc of the selected dates (inclusive business-day span), not editable.
  const days =
    !task.is_milestone && task.planned_start && task.planned_finish
      ? businessDays(task.planned_start, task.planned_finish)
      : 0;
  const float = task.total_float ?? null;
  const floatStyle: CSSProperties = {
    ...cellCenter,
    width: FLOAT_W,
    color: float !== null && float < 0 ? "var(--red)" : "var(--text-2)",
    fontWeight: float !== null && float < 0 ? 600 : 400,
  };

  const rowClass = `task-grid__row${change ? ` task-grid__row--${change}` : ""}`;

  return (
    <div className={rowClass} style={bodyRowStyle}>
      <LeadCells
        nameWidth={nameWidth}
        wbs={row.code}
        name={task.name}
        from={task.planned_start}
        to={task.planned_finish}
        days={days}
        isMilestone={task.is_milestone}
        depth={row.depth}
        onCommitName={
          readOnly
            ? undefined
            : (v) => {
                if (v) onUpdate(task.id, { name: v });
              }
        }
        onCommitFrom={readOnly ? undefined : (v) => onUpdate(task.id, { actual_start: v || null })}
        onCommitTo={readOnly ? undefined : (v) => onUpdate(task.id, { actual_finish: v || null })}
        afterName={
          <div style={{ ...cellBase, width: TRADE_W, padding: 0, overflow: "visible" }}>
            {readOnly ? (
              <span style={{ ...cellBase, width: TRADE_W, color: "var(--text-2)" }}>
                {task.trade ?? "—"}
              </span>
            ) : (
              <TradeCell
                value={task.trade ?? ""}
                trades={trades}
                onCommit={(v) => onUpdate(task.id, { trade: v || null })}
              />
            )}
          </div>
        }
      />
      <div style={floatStyle}>{float ?? "—"}</div>
      <div style={{ ...cellCenter, width: PCT_W, padding: 0, overflow: "visible" }}>
        {readOnly ? (
          <span style={{ color: "var(--text-2)" }}>{Math.round(task.percent_complete)}</span>
        ) : (
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
        )}
      </div>
      <div style={{ ...cellCenter, width: CRIT_W, color: "var(--red)" }}>
        {task.is_critical ? "●" : ""}
      </div>
      <div style={{ ...cellBase, width: DEL_W }}>
        {!readOnly && (
          <button className="link-danger" onClick={() => onDelete(task.id)}>
            delete
          </button>
        )}
      </div>
    </div>
  );
}

// ---- Trade typeahead ----------------------------------------------------------

function isSubsequence(q: string, t: string): boolean {
  if (!q) return true;
  let i = 0;
  for (const c of t) {
    if (c === q[i]) i += 1;
    if (i === q.length) return true;
  }
  return false;
}

// Rank trades by how closely they match the query: exact < prefix < substring <
// fuzzy subsequence. Empty query returns the full list (so focus shows all trades).
function fuzzyTrades(query: string, trades: string[]): string[] {
  const q = query.trim().toLowerCase();
  if (!q) return [...trades].sort((a, b) => a.localeCompare(b));
  const scored: { t: string; score: number }[] = [];
  for (const t of trades) {
    const lt = t.toLowerCase();
    let score = -1;
    if (lt === q) score = 0;
    else if (lt.startsWith(q)) score = 1;
    else if (lt.includes(q)) score = 2;
    else if (isSubsequence(q, lt)) score = 3;
    if (score >= 0) scored.push({ t, score });
  }
  scored.sort((a, b) => a.score - b.score || a.t.localeCompare(b.t));
  return scored.map((s) => s.t);
}

function TradeCell({
  value,
  trades,
  onCommit,
}: {
  value: string;
  trades: string[];
  onCommit: (value: string) => void;
}) {
  const [draft, setDraft] = useState(value);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const cancel = useRef(false);
  useEffect(() => setDraft(value), [value]);

  const matches = useMemo(
    () => fuzzyTrades(draft, trades).filter((t) => t !== value).slice(0, 6),
    [draft, trades, value],
  );

  const commit = (v: string) => {
    cancel.current = true; // suppress the trailing onBlur commit
    setOpen(false);
    setDraft(v);
    if (v.trim() !== value) onCommit(v.trim());
  };

  return (
    <div className="trade-cell">
      <input
        className="cell-input"
        value={draft}
        placeholder="—"
        aria-label="Trade"
        onClick={(e) => e.stopPropagation()}
        onFocus={() => {
          cancel.current = false;
          setOpen(true);
          setActive(0);
        }}
        onChange={(e) => {
          cancel.current = false;
          setDraft(e.target.value);
          setOpen(true);
          setActive(0);
        }}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") {
            e.preventDefault();
            setActive((a) => Math.min(a + 1, matches.length - 1));
          } else if (e.key === "ArrowUp") {
            e.preventDefault();
            setActive((a) => Math.max(a - 1, 0));
          } else if (e.key === "Enter") {
            e.preventDefault();
            commit(open && matches[active] ? matches[active] : draft);
            e.currentTarget.blur();
          } else if (e.key === "Escape") {
            cancel.current = true;
            setDraft(value);
            setOpen(false);
            e.currentTarget.blur();
          }
        }}
        onBlur={() => {
          setOpen(false);
          if (cancel.current) {
            cancel.current = false;
            return;
          }
          if (draft.trim() !== value) onCommit(draft.trim());
        }}
      />
      {open && matches.length > 0 && (
        <div className="trade-suggest">
          {matches.map((m, i) => (
            <button
              key={m}
              className={i === active ? "active" : ""}
              // mousedown (not click) so it fires before the input's blur
              onMouseDown={(e) => {
                e.preventDefault();
                commit(m);
              }}
            >
              {m}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
