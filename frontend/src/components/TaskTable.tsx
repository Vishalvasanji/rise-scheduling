// Read/edit task grid — an Excel / MS-Project-style spreadsheet. The grid is
// READ-ONLY until an edit session is started (the toolbar pencil); then the cells
// (Name · From · To · Days · Trade · % · Status) edit directly and stage into a
// draft, and pressing Save pushes every change at once. The first columns (WBS ·
// Task · Building · From · To · Days) are the shared lead block rendered identically
// to the Gantt list; the rest are grid-only. WBS, Float and Critical are
// engine-computed / read-only, as are WBS roll-up group rows.

import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import type { ChangeType, DependencyOut, TaskOut, TaskStatus } from "../types/schedule";
import type { GroupRow, Row, TaskRow } from "../lib/rollup";
import { businessDays, mmddyy } from "../lib/dates";
import { applyDraft, startFieldForEdit } from "../lib/task";
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
  /** Whether an edit session is active (cells editable, staging into the draft). */
  editMode: boolean;
  /** Per-task staged edits, overlaid for display; a field present => dirty cell. */
  draft: Map<number, Partial<TaskOut>>;
  /** Stage a change into the draft (does NOT hit the server until Save). */
  onCell: (taskId: number, fields: Partial<TaskOut>) => void;
  /** Create a task under the given group (edit mode; applies immediately). */
  onAdd?: (groupCode: string) => void;
  onDelete: (taskId: number) => void;
  /** Project dependencies, for the Preds column. */
  dependencies?: DependencyOut[];
  /** Task id -> display ref (WBS or name) for predecessor chips. */
  predLabel?: (taskId: number) => string;
  /** Edit mode: parse a typed ref ("1.1.3", "1.1.3 SS+1") and link it (immediate). */
  onAddDep?: (successorId: number, text: string) => void;
  /** Edit mode: remove a dependency by id (immediate). */
  onRemoveDep?: (dependencyId: number) => void;
  /** Review mode: task id -> change kind. Present => tint rows + read-only. */
  changeStatus?: Map<number, ChangeType>;
}

// Trailing (grid-only) column widths.
const TRADE_W = 140;
const PRED_W = 150;
const FLOAT_W = 64;
const PCT_W = 64;
const STATUS_W = 116;
const CRIT_W = 64;
const DEL_W = 72;

const trailingWidth = TRADE_W + PRED_W + FLOAT_W + PCT_W + STATUS_W + CRIT_W + DEL_W;

// "Trade" header / cell, placed right after Task via the LeadCells afterName slot.
const tradeHeader = <div style={{ ...cellBase, width: TRADE_W }}>Trade</div>;

const NO_DEPS: DependencyOut[] = [];

// Chip label suffix: nothing for a plain FS+0 link, else the type and signed lag.
function depSuffix(d: DependencyOut): string {
  if (d.type === "FS" && d.lag_days === 0) return "";
  const lag = d.lag_days === 0 ? "" : d.lag_days > 0 ? `+${d.lag_days}` : String(d.lag_days);
  return ` ${d.type}${lag}`;
}

const STATUS_OPTS: { value: TaskStatus; label: string }[] = [
  { value: "not_started", label: "Not started" },
  { value: "in_progress", label: "In progress" },
  { value: "complete", label: "Complete" },
  { value: "blocked", label: "Blocked" },
];
const statusLabel = (s: TaskStatus) => STATUS_OPTS.find((o) => o.value === s)?.label ?? s;

export function TaskTable({
  rows,
  trades,
  collapsed,
  onToggle,
  editMode,
  draft,
  onCell,
  onAdd,
  onDelete,
  dependencies,
  predLabel,
  onAddDep,
  onRemoveDep,
  changeStatus,
}: Props) {
  const { nameWidth, onResizeStart } = useSharedNameWidth();
  const minWidth = leadWidth(nameWidth) + trailingWidth;
  const review = !!changeStatus;
  const editable = editMode && !review;

  // Successor -> its dependency rows, for the Preds column.
  const depsBySucc = useMemo(() => {
    const m = new Map<number, DependencyOut[]>();
    for (const d of dependencies ?? []) {
      const list = m.get(d.successor_id) ?? m.set(d.successor_id, []).get(d.successor_id)!;
      list.push(d);
    }
    return m;
  }, [dependencies]);

  return (
    <div className="task-grid" style={{ minWidth, fontSize: "13px" }}>
      <div className="task-grid__header" style={headerRowStyle}>
        <LeadHeader nameWidth={nameWidth} onResizeStart={onResizeStart} afterName={tradeHeader} />
        <div style={{ ...cellBase, width: PRED_W }}>Preds</div>
        <div style={{ ...cellCenter, width: FLOAT_W }}>Float</div>
        <div style={{ ...cellCenter, width: PCT_W }}>%</div>
        <div style={{ ...cellCenter, width: STATUS_W }}>Status</div>
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
            onAdd={editable && onAdd ? () => onAdd(r.code) : undefined}
          />
        ) : (
          <Line
            key={r.id}
            row={r}
            nameWidth={nameWidth}
            trades={trades}
            editable={editable}
            draftFields={draft.get(r.task.id)}
            onCell={onCell}
            onDelete={onDelete}
            deps={depsBySucc.get(r.task.id) ?? NO_DEPS}
            predLabel={predLabel}
            onAddDep={onAddDep}
            onRemoveDep={onRemoveDep}
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
  onAdd,
}: {
  row: GroupRow;
  nameWidth: number;
  collapsed: boolean;
  onToggle: () => void;
  onAdd?: () => void;
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
        onAddChild={onAdd}
        afterName={<div style={{ ...cellBase, width: TRADE_W }} />}
      />
      <div style={{ ...cellBase, width: PRED_W }} />
      <div style={{ ...cellCenter, width: FLOAT_W, color: "var(--text-3)" }}>—</div>
      <div style={{ ...cellCenter, width: PCT_W, color: "var(--text-2)" }}>{Math.round(row.percent)}</div>
      <div style={{ ...cellCenter, width: STATUS_W, color: "var(--text-3)" }}>—</div>
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
  editable,
  draftFields,
  onCell,
  onDelete,
  deps,
  predLabel,
  onAddDep,
  onRemoveDep,
  change,
}: {
  row: TaskRow;
  nameWidth: number;
  trades: string[];
  editable: boolean;
  draftFields?: Partial<TaskOut>;
  onCell: Props["onCell"];
  onDelete: Props["onDelete"];
  deps: DependencyOut[];
  predLabel?: (taskId: number) => string;
  onAddDep?: Props["onAddDep"];
  onRemoveDep?: Props["onRemoveDep"];
  change?: ChangeType;
}) {
  const base = row.task;
  // Display values overlay any staged draft so edited cells show the typed value.
  const task = applyDraft(base, draftFields);
  const has = (f: keyof TaskOut) => !!draftFields && f in draftFields;
  const dirtyFrom = has("actual_start") || has("start_no_earlier_than");

  // In edit mode Days shows the editable duration; otherwise the planned span.
  const days = editable
    ? task.duration_days
    : !task.is_milestone && task.planned_start && task.planned_finish
      ? businessDays(task.planned_start, task.planned_finish)
      : 0;
  const float = base.total_float ?? null;
  const floatStyle: CSSProperties = {
    ...cellCenter,
    width: FLOAT_W,
    color: float !== null && float < 0 ? "var(--red)" : "var(--text-2)",
    fontWeight: float !== null && float < 0 ? 600 : 400,
  };

  const dirtyRow = !!draftFields && Object.keys(draftFields).length > 0;
  const rowClass =
    `task-grid__row${change ? ` task-grid__row--${change}` : ""}` +
    (dirtyRow ? " task-grid__row--dirty" : "");

  return (
    <div className={rowClass} style={bodyRowStyle}>
      <LeadCells
        nameWidth={nameWidth}
        wbs={row.code}
        name={task.name}
        building={task.building}
        from={task.planned_start}
        to={task.planned_finish}
        days={days}
        isMilestone={task.is_milestone}
        depth={row.depth}
        startConstrained={!task.is_milestone && !!task.start_no_earlier_than}
        constraintLabel={
          task.start_no_earlier_than
            ? `Earliest start: ${mmddyy(task.start_no_earlier_than)}`
            : undefined
        }
        dirtyName={has("name")}
        dirtyBuilding={has("building")}
        dirtyFrom={dirtyFrom}
        dirtyTo={has("actual_finish")}
        dirtyDays={has("duration_days")}
        onCommitName={
          editable
            ? (v) => {
                if (v) onCell(base.id, { name: v });
              }
            : undefined
        }
        onCommitBuilding={
          editable ? (v) => onCell(base.id, { building: v || null }) : undefined
        }
        onCommitFrom={editable ? (v) => onCell(base.id, startFieldForEdit(base, v)) : undefined}
        onCommitTo={editable ? (v) => onCell(base.id, { actual_finish: v || null }) : undefined}
        onCommitDays={
          editable
            ? (v) => {
                const n = Number(v);
                if (Number.isFinite(n) && n >= 1) onCell(base.id, { duration_days: n });
              }
            : undefined
        }
        afterName={
          <div style={{ ...cellBase, width: TRADE_W, padding: 0, overflow: "visible" }}>
            {editable ? (
              <TradeCell
                value={task.trade ?? ""}
                trades={trades}
                dirty={has("trade")}
                onCommit={(v) => onCell(base.id, { trade: v || null })}
              />
            ) : (
              // Plain text (not a nested cellBase — that would draw a second gridline
              // inside the cell); the column's border lives on the outer cell div.
              <span
                style={{
                  padding: "0 8px",
                  color: "var(--text-2)",
                  overflow: "hidden",
                  whiteSpace: "nowrap",
                  textOverflow: "ellipsis",
                }}
              >
                {task.trade ?? "—"}
              </span>
            )}
          </div>
        }
      />
      <PredsCell
        deps={deps}
        editable={editable}
        label={predLabel ?? String}
        onAdd={onAddDep ? (text) => onAddDep(base.id, text) : undefined}
        onRemove={onRemoveDep}
      />
      <div style={floatStyle}>{float ?? "—"}</div>
      <div style={{ ...cellCenter, width: PCT_W, padding: 0, overflow: "visible" }}>
        {editable ? (
          <CellInput
            value={String(task.percent_complete)}
            type="number"
            min={0}
            max={100}
            align="center"
            ariaLabel="Percent complete"
            dirty={has("percent_complete")}
            onCommit={(v) => {
              const n = Number(v);
              if (Number.isFinite(n) && n >= 0 && n <= 100)
                onCell(base.id, { percent_complete: n });
            }}
          />
        ) : (
          <span style={{ color: "var(--text-2)" }}>{Math.round(task.percent_complete)}</span>
        )}
      </div>
      <div style={{ ...cellCenter, width: STATUS_W, padding: 0, overflow: "visible" }}>
        {editable ? (
          <StatusCell
            value={task.status}
            dirty={has("status")}
            onCommit={(v) => onCell(base.id, { status: v })}
          />
        ) : (
          <span style={{ color: "var(--text-2)" }}>{statusLabel(task.status)}</span>
        )}
      </div>
      <div style={{ ...cellCenter, width: CRIT_W, color: "var(--red)" }}>
        {base.is_critical ? "●" : ""}
      </div>
      <div style={{ ...cellBase, width: DEL_W, gap: 6 }}>
        {editable && (
          <>
            <button
              className={task.is_milestone ? "milestone-toggle milestone-toggle--on" : "milestone-toggle"}
              title={task.is_milestone ? "Convert to regular task" : "Convert to milestone"}
              aria-label={task.is_milestone ? "Convert to regular task" : "Convert to milestone"}
              onClick={() =>
                onCell(
                  base.id,
                  task.is_milestone
                    ? { is_milestone: false, duration_days: 1 }
                    : { is_milestone: true, duration_days: 0 },
                )
              }
            >
              ◆
            </button>
            <button className="link-danger" onClick={() => onDelete(base.id)}>
              delete
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// Predecessors cell: chips like "1.1.3", "1.1.3 SS+1" (WBS ref + non-default
// type/lag). In edit mode each chip gets an × (removes the link immediately) and
// a small input accepts a typed ref — "1.1.3", "1.1.3 SS", "1.1.3 FF+2" — that
// links on Enter. The engine rejects cycles server-side (banner shows why).
function PredsCell({
  deps,
  editable,
  label,
  onAdd,
  onRemove,
}: {
  deps: DependencyOut[];
  editable: boolean;
  label: (taskId: number) => string;
  onAdd?: (text: string) => void;
  onRemove?: (dependencyId: number) => void;
}) {
  const [text, setText] = useState("");
  return (
    <div style={{ ...cellBase, width: PRED_W, gap: 4, overflow: "hidden" }}>
      {deps.map((d) => (
        <span key={d.id} className="pred-chip" title={`${label(d.predecessor_id)} ${d.type}${d.lag_days ? ` lag ${d.lag_days}d` : ""}`}>
          {label(d.predecessor_id)}
          {depSuffix(d)}
          {editable && onRemove ? (
            <button
              className="pred-chip__x"
              aria-label={`Remove predecessor ${label(d.predecessor_id)}`}
              onClick={(e) => {
                e.stopPropagation();
                onRemove(d.id);
              }}
            >
              ×
            </button>
          ) : null}
        </span>
      ))}
      {editable && onAdd ? (
        <input
          className="pred-add"
          value={text}
          placeholder="+ wbs"
          aria-label="Add predecessor"
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            e.stopPropagation();
            if (e.key === "Enter" && text.trim()) {
              onAdd(text.trim());
              setText("");
            } else if (e.key === "Escape") {
              setText("");
              e.currentTarget.blur();
            }
          }}
        />
      ) : null}
    </div>
  );
}

// Status dropdown (edit mode). A native select keeps it familiar and keyboard-usable.
function StatusCell({
  value,
  dirty,
  onCommit,
}: {
  value: TaskStatus;
  dirty?: boolean;
  onCommit: (value: TaskStatus) => void;
}) {
  return (
    <select
      className={dirty ? "cell-select cell-select--dirty" : "cell-select"}
      value={value}
      aria-label="Status"
      onClick={(e) => e.stopPropagation()}
      onChange={(e) => onCommit(e.target.value as TaskStatus)}
    >
      {STATUS_OPTS.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
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
  dirty,
  onCommit,
}: {
  value: string;
  trades: string[];
  dirty?: boolean;
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
        className={dirty ? "cell-input cell-input--dirty" : "cell-input"}
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
