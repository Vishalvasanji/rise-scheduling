// Shared "lead" columns (WBS · Task · From · To · Days) rendered identically by
// both the Gantt task list (GanttView) and the Task grid (TaskTable), so toggling
// the two views only changes what comes *after* these five columns. Colors come
// from the CSS custom properties so the two views stay on one design system.

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  CSSProperties,
  FC,
  KeyboardEvent as ReactKeyboardEvent,
  MouseEvent as ReactMouseEvent,
  ReactNode,
} from "react";
import { mmddyy, parseTypedDate } from "../lib/dates";

// Fixed widths (Task is the only adjustable one).
export const WBS_W = 56;
export const BUILDING_W = 120;
export const FROM_W = 74;
export const TO_W = 74;
export const DAYS_W = 58;
export const NAME_MIN = 90;
export const NAME_MAX = 480;
export const NAME_DEFAULT = 170;

export const leadWidth = (nameW: number) =>
  WBS_W + nameW + BUILDING_W + FROM_W + TO_W + DAYS_W;

export const HEADER_H = 42;
export const ROW_H = 38;
export const FONT_SIZE = "13px";

const NAME_KEY = "rise_task_name_w";

// Excel-style column-header band: gray fill, bold, framed by gridlines. The left
// border closes the grid's left edge (cells carry only a right border); the bottom
// border is the header/body divider in the shared gridline gray.
export const headerRowStyle: CSSProperties = {
  display: "flex",
  // Stretch so each cell fills the full row height and its right-border gridline
  // is a continuous vertical line (cells re-center their own content via cellBase).
  alignItems: "stretch",
  height: HEADER_H,
  fontSize: FONT_SIZE,
  fontWeight: 600,
  color: "var(--text-2)",
  background: "var(--grid-header-bg)",
  borderTop: "1px solid var(--grid-line)",
  borderLeft: "1px solid var(--grid-line)",
  borderBottom: "1px solid var(--grid-line)",
  boxSizing: "border-box",
};

// A spreadsheet row: horizontal gridline underneath, left edge closed to match the
// header. Per-cell right borders draw the vertical gridlines.
export const bodyRowStyle: CSSProperties = {
  display: "flex",
  alignItems: "stretch",
  height: ROW_H,
  borderLeft: "1px solid var(--grid-line)",
  borderBottom: "1px solid var(--grid-line)",
  boxSizing: "border-box",
};

// Every cell carries a right gridline, so header + body + empty spacer cells all read
// as boxed spreadsheet cells (Excel draws lines through blanks too).
export const cellBase: CSSProperties = {
  display: "flex",
  alignItems: "center",
  padding: "0 8px",
  overflow: "hidden",
  whiteSpace: "nowrap",
  textOverflow: "ellipsis",
  borderRight: "1px solid var(--grid-line)",
  boxSizing: "border-box",
};

// From/To/Days center their short values horizontally.
export const cellCenter: CSSProperties = { ...cellBase, justifyContent: "center" };

// Just the drag hit-area; the Task cell's own right gridline is the visible divider.
const resizeHandle: CSSProperties = {
  position: "absolute",
  top: 0,
  right: 0,
  height: "100%",
  width: 9,
  cursor: "col-resize",
};

// Resizable, persisted Task-column width. Both tabs read the same localStorage key,
// and they're never mounted at once (ProjectPage toggles), so dragging in one view
// and switching tabs carries the width to the other.
export function useSharedNameWidth() {
  const [nameWidth, setNameWidth] = useState<number>(() => {
    const v = Number(localStorage.getItem(NAME_KEY));
    return v >= NAME_MIN && v <= NAME_MAX ? v : NAME_DEFAULT;
  });

  useEffect(() => {
    localStorage.setItem(NAME_KEY, String(nameWidth));
  }, [nameWidth]);

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

  return { nameWidth, onResizeStart };
}

// Spreadsheet-style navigation between editable cells. Left/Right walk document
// order (a row reads left-to-right); Up/Down move within the same column by
// matching the cell's horizontal position. On arrival the target's text is
// selected, so typing replaces it — exactly like moving the selection in Excel.
export type CellDir = "up" | "down" | "left" | "right";

// The spreadsheet-navigation intent of a keypress in an editable cell, or null if
// the key should edit within the cell. Up/Down always leave; Enter drops down;
// Left/Right leave only when the caret sits at the text edge (number inputs can't
// report a caret, so they always leave). Shared by every editable cell.
export function cellNavDir(e: ReactKeyboardEvent<HTMLInputElement>): CellDir | null {
  const el = e.currentTarget;
  const num = el.type === "number";
  const atStart = num || el.selectionStart === 0;
  const atEnd = num || el.selectionEnd === el.value.length;
  if (e.key === "Enter" || e.key === "ArrowDown") return "down";
  if (e.key === "ArrowUp") return "up";
  if (e.key === "ArrowLeft" && atStart) return "left";
  if (e.key === "ArrowRight" && atEnd) return "right";
  return null;
}

export function focusCell(current: HTMLElement, dir: CellDir): void {
  const cells = Array.from(
    document.querySelectorAll<HTMLElement>(".cell-input:not([disabled])"),
  );
  let target: HTMLElement | undefined;
  if (dir === "left" || dir === "right") {
    const i = cells.indexOf(current);
    target = dir === "right" ? cells[i + 1] : cells[i - 1];
  } else {
    const left = current.getBoundingClientRect().left;
    const col = cells
      .filter((c) => Math.abs(c.getBoundingClientRect().left - left) < 4)
      .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top);
    const i = col.indexOf(current);
    target = dir === "down" ? col[i + 1] : col[i - 1];
  }
  if (target) {
    target.focus();
    try {
      (target as HTMLInputElement).select();
    } catch {
      /* not a text-selectable input */
    }
  }
}

// ---- Inline click-to-edit cell ------------------------------------------------
// A borderless input that looks like plain text until hovered/focused, so every
// editable field "changes on click" with no dropdowns or persistent boxes. Commits
// on blur / Enter (Enter also advances to the next cell); Escape cancels. Caller
// parses the string value. `dirty` tints the cell while it holds an unsaved edit.

export const CellInput: FC<{
  value: string;
  type?: "text" | "number";
  placeholder?: string;
  min?: number;
  max?: number;
  align?: "left" | "center";
  ariaLabel?: string;
  dirty?: boolean;
  style?: CSSProperties;
  onCommit: (value: string) => void;
}> = ({
  value,
  type = "text",
  placeholder,
  min,
  max,
  align = "left",
  ariaLabel,
  dirty,
  style,
  onCommit,
}) => {
  const [draft, setDraft] = useState(value);
  const cancel = useRef(false);
  const nav = useRef<CellDir | null>(null);
  useEffect(() => setDraft(value), [value]);
  return (
    <input
      className={dirty ? "cell-input cell-input--dirty" : "cell-input"}
      type={type}
      value={draft}
      min={min}
      max={max}
      placeholder={placeholder}
      aria-label={ariaLabel}
      style={{ textAlign: align, ...style }}
      onChange={(e) => setDraft(e.target.value)}
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          cancel.current = true;
          e.currentTarget.blur();
          return;
        }
        const dir = cellNavDir(e);
        if (dir) {
          e.preventDefault();
          nav.current = dir;
          e.currentTarget.blur();
        }
      }}
      onBlur={(e) => {
        if (cancel.current) {
          cancel.current = false;
          setDraft(value);
          return;
        }
        if (draft.trim() !== value) onCommit(draft.trim());
        const dir = nav.current;
        nav.current = null;
        if (dir) focusCell(e.currentTarget, dir);
      }}
    />
  );
};

// A date cell that behaves like the others: it's a text input (so it joins arrow-key
// navigation and shows MM/DD/YY at the column's width), you type the date and it's
// parsed on commit, and — only on a mouse click — a native date picker opens instead
// of a text caret. `value` and the committed string are ISO (YYYY-MM-DD); clearing
// the text commits "". The hidden `type="date"` input exists solely to host the picker.
export const DateInput: FC<{
  value: string | null;
  ariaLabel?: string;
  dirty?: boolean;
  onCommit: (value: string) => void;
}> = ({ value, ariaLabel, dirty, onCommit }) => {
  const [draft, setDraft] = useState(value ? mmddyy(value) : "");
  const cancel = useRef(false);
  const nav = useRef<CellDir | null>(null);
  const picker = useRef<HTMLInputElement>(null);
  useEffect(() => setDraft(value ? mmddyy(value) : ""), [value]);

  const commitText = () => {
    const t = draft.trim();
    if (t === "") {
      if (value) onCommit(""); // cleared
      return;
    }
    const iso = parseTypedDate(t);
    if (iso && iso !== value) onCommit(iso);
    else setDraft(value ? mmddyy(value) : ""); // normalize, or revert an unparseable typo
  };

  const openPicker = () => {
    const el = picker.current as (HTMLInputElement & { showPicker?: () => void }) | null;
    if (!el) return;
    el.focus();
    try {
      el.showPicker?.();
    } catch {
      /* showPicker unavailable — the native control still works */
    }
  };

  return (
    <div className="date-cell">
      <input
        className={dirty ? "cell-input cell-input--dirty" : "cell-input"}
        value={draft}
        placeholder="mm/dd/yy"
        aria-label={ariaLabel}
        style={{ textAlign: "center", paddingRight: 16 }}
        onChange={(e) => setDraft(e.target.value)}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            cancel.current = true;
            e.currentTarget.blur();
            return;
          }
          const dir = cellNavDir(e);
          if (dir) {
            e.preventDefault();
            nav.current = dir;
            e.currentTarget.blur();
          }
        }}
        onBlur={(e) => {
          if (cancel.current) {
            cancel.current = false;
            setDraft(value ? mmddyy(value) : "");
            return;
          }
          commitText();
          const dir = nav.current;
          nav.current = null;
          if (dir) focusCell(e.currentTarget, dir);
        }}
      />
      {/* Calendar affordance: opens the native picker without stealing typing focus. */}
      <button
        type="button"
        className="date-cell__pick"
        tabIndex={-1}
        aria-label="Open date picker"
        onMouseDown={(e) => {
          e.preventDefault();
          e.stopPropagation();
          openPicker();
        }}
      >
        📅
      </button>
      <input
        ref={picker}
        type="date"
        className="date-picker-overlay"
        tabIndex={-1}
        aria-hidden
        value={value ?? ""}
        onChange={(e) => onCommit(e.target.value)}
      />
    </div>
  );
};

// ---- The five shared columns --------------------------------------------------

export const LeadHeader: FC<{
  nameWidth: number;
  onResizeStart: (e: ReactMouseEvent) => void;
  // Optional column(s) inserted right after Task (Task grid only, e.g. Trade).
  afterName?: ReactNode;
}> = ({ nameWidth, onResizeStart, afterName }) => (
  <>
    <div style={{ ...cellBase, width: WBS_W }}>WBS</div>
    <div style={{ ...cellBase, width: nameWidth, position: "relative" }}>
      Task
      <span style={resizeHandle} onMouseDown={onResizeStart} />
    </div>
    <div style={{ ...cellBase, width: BUILDING_W }}>Building</div>
    {afterName}
    <div style={{ ...cellCenter, width: FROM_W }}>From</div>
    <div style={{ ...cellCenter, width: TO_W }}>To</div>
    <div style={{ ...cellCenter, width: DAYS_W }}>Days</div>
  </>
);

// A roll-up group row gets a clickable caret + bold name; both group and leaf rows
// indent the Task cell by `depth` so the WBS hierarchy reads visually.
const caretStyle: CSSProperties = {
  display: "inline-flex",
  width: 14,
  marginLeft: -2,
  marginRight: 2,
  color: "var(--text-3)",
  cursor: "pointer",
  fontSize: 10,
  userSelect: "none",
  flexShrink: 0,
};

export const LeadCells: FC<{
  nameWidth: number;
  wbs: string;
  name: string;
  building?: string | null;
  from: string | Date | null;
  to: string | Date | null;
  days: number;
  isMilestone: boolean;
  depth?: number;
  isGroup?: boolean;
  collapsed?: boolean;
  onToggle?: () => void;
  // When provided (Task grid only), these cells edit inline on click.
  onCommitName?: (value: string) => void;
  onCommitBuilding?: (value: string) => void;
  onCommitDays?: (value: string) => void;
  onCommitFrom?: (value: string) => void;
  onCommitTo?: (value: string) => void;
  // Marks the start as pinned by a "start no earlier than" constraint.
  startConstrained?: boolean;
  constraintLabel?: string;
  // Per-field unsaved-edit tint (edit sessions).
  dirtyName?: boolean;
  dirtyBuilding?: boolean;
  dirtyFrom?: boolean;
  dirtyTo?: boolean;
  dirtyDays?: boolean;
  // Optional column(s) inserted right after Task (Task grid only, e.g. Trade).
  afterName?: ReactNode;
}> = ({
  nameWidth,
  wbs,
  name,
  building,
  from,
  to,
  days,
  isMilestone,
  depth = 0,
  isGroup,
  collapsed,
  onToggle,
  onCommitName,
  onCommitBuilding,
  onCommitDays,
  onCommitFrom,
  onCommitTo,
  startConstrained,
  constraintLabel,
  dirtyName,
  dirtyBuilding,
  dirtyFrom,
  dirtyTo,
  dirtyDays,
  afterName,
}) => {
  const indent = 8 + depth * 14;
  const editName = !isGroup && !!onCommitName;
  const editBuilding = !isGroup && !!onCommitBuilding;
  const editDays = !isGroup && !isMilestone && !!onCommitDays;
  const editFrom = !isGroup && !!onCommitFrom;
  const editTo = !isGroup && !!onCommitTo;
  const fromStr = typeof from === "string" ? from : null;
  const toStr = typeof to === "string" ? to : null;
  return (
    <>
      <div style={{ ...cellBase, width: WBS_W, color: "var(--text-3)" }}>{wbs}</div>
      <div
        style={{
          ...cellBase,
          width: nameWidth,
          padding: editName ? 0 : "0 8px",
          paddingLeft: editName ? undefined : indent,
          overflow: editName ? "visible" : "hidden",
          fontWeight: isGroup ? 600 : undefined,
        }}
        title={name}
      >
        {isGroup ? (
          <span
            style={caretStyle}
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => {
              e.stopPropagation();
              onToggle?.();
            }}
          >
            {collapsed ? "▶" : "▼"}
          </span>
        ) : null}
        {editName ? (
          <CellInput
            value={name}
            ariaLabel="Task name"
            dirty={dirtyName}
            style={{ paddingLeft: indent }}
            onCommit={onCommitName!}
          />
        ) : (
          <>
            {!isGroup && isMilestone ? "◆ " : ""}
            {name}
          </>
        )}
      </div>
      <div
        style={{
          ...cellBase,
          width: BUILDING_W,
          color: "var(--text-2)",
          padding: editBuilding ? 0 : undefined,
          overflow: editBuilding ? "visible" : "hidden",
        }}
        title={building ?? ""}
      >
        {editBuilding ? (
          <CellInput
            value={building ?? ""}
            ariaLabel="Building"
            dirty={dirtyBuilding}
            onCommit={onCommitBuilding!}
          />
        ) : (
          building || ""
        )}
      </div>
      {afterName}
      <div
        title={startConstrained ? constraintLabel : undefined}
        style={{
          ...cellCenter,
          width: FROM_W,
          color: "var(--text-2)",
          padding: editFrom ? 0 : undefined,
          overflow: editFrom ? "visible" : "hidden",
          position: editFrom || startConstrained ? "relative" : undefined,
        }}
      >
        {startConstrained && (
          <span
            aria-hidden
            style={{
              position: "absolute",
              left: 3,
              top: 3,
              fontSize: 8,
              lineHeight: 1,
              color: "var(--amber-ink)",
              pointerEvents: "none",
            }}
          >
            ●
          </span>
        )}
        {editFrom ? (
          <DateInput value={fromStr} ariaLabel="Start date" dirty={dirtyFrom} onCommit={onCommitFrom!} />
        ) : from ? (
          mmddyy(from)
        ) : (
          "—"
        )}
      </div>
      <div
        style={{
          ...cellCenter,
          width: TO_W,
          color: "var(--text-2)",
          padding: editTo ? 0 : undefined,
          overflow: editTo ? "visible" : "hidden",
          position: editTo ? "relative" : undefined,
        }}
      >
        {editTo ? (
          <DateInput value={toStr} ariaLabel="Finish date" dirty={dirtyTo} onCommit={onCommitTo!} />
        ) : to ? (
          mmddyy(to)
        ) : (
          "—"
        )}
      </div>
      <div
        style={{
          ...cellCenter,
          width: DAYS_W,
          color: "var(--text-2)",
          padding: editDays ? 0 : undefined,
          overflow: editDays ? "visible" : "hidden",
        }}
      >
        {editDays ? (
          <CellInput
            value={String(days)}
            type="number"
            min={0}
            align="center"
            ariaLabel="Duration in days"
            dirty={dirtyDays}
            onCommit={onCommitDays!}
          />
        ) : !isGroup && (isMilestone || !days) ? (
          "—"
        ) : (
          days || "—"
        )}
      </div>
    </>
  );
};
