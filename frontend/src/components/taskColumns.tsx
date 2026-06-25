// Shared "lead" columns (WBS · Task · From · To · Days) rendered identically by
// both the Gantt task list (GanttView) and the Task grid (TaskTable), so toggling
// the two views only changes what comes *after* these five columns. Colors come
// from the CSS custom properties so the two views stay on one design system.

import { useCallback, useEffect, useRef, useState } from "react";
import type { CSSProperties, FC, MouseEvent as ReactMouseEvent } from "react";
import { mmddyy } from "../lib/dates";

// Fixed widths (Task is the only adjustable one).
export const WBS_W = 56;
export const FROM_W = 74;
export const TO_W = 74;
export const DAYS_W = 58;
export const NAME_MIN = 90;
export const NAME_MAX = 480;
export const NAME_DEFAULT = 170;

export const leadWidth = (nameW: number) => WBS_W + nameW + FROM_W + TO_W + DAYS_W;

export const HEADER_H = 42;
export const ROW_H = 38;
export const FONT_SIZE = "13px";

const NAME_KEY = "rise_task_name_w";

export const headerRowStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  height: HEADER_H,
  fontSize: FONT_SIZE,
  fontWeight: 600,
  color: "var(--text-2)",
  background: "var(--surface-2)",
  borderBottom: "1px solid var(--separator)",
  boxSizing: "border-box",
};

export const bodyRowStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  height: ROW_H,
  borderBottom: "1px solid var(--separator)",
  boxSizing: "border-box",
};

export const cellBase: CSSProperties = {
  display: "flex",
  alignItems: "center",
  padding: "0 8px",
  overflow: "hidden",
  whiteSpace: "nowrap",
  textOverflow: "ellipsis",
};

// From/To/Days center their short values horizontally.
export const cellCenter: CSSProperties = { ...cellBase, justifyContent: "center" };

const resizeHandle: CSSProperties = {
  position: "absolute",
  top: 0,
  right: 0,
  height: "100%",
  width: 9,
  cursor: "col-resize",
  borderRight: "1px solid var(--separator-strong)",
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

// ---- Inline click-to-edit cell ------------------------------------------------
// A borderless input that looks like plain text until hovered/focused, so every
// editable field "changes on click" with no dropdowns or persistent boxes. Commits
// on blur / Enter; Escape cancels. Caller parses the string value.

export const CellInput: FC<{
  value: string;
  type?: "text" | "number";
  placeholder?: string;
  min?: number;
  max?: number;
  align?: "left" | "center";
  ariaLabel?: string;
  style?: CSSProperties;
  onCommit: (value: string) => void;
}> = ({ value, type = "text", placeholder, min, max, align = "left", ariaLabel, style, onCommit }) => {
  const [draft, setDraft] = useState(value);
  const cancel = useRef(false);
  useEffect(() => setDraft(value), [value]);
  return (
    <input
      className="cell-input"
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
        if (e.key === "Enter") e.currentTarget.blur();
        else if (e.key === "Escape") {
          cancel.current = true;
          e.currentTarget.blur();
        }
      }}
      onBlur={() => {
        if (cancel.current) {
          cancel.current = false;
          setDraft(value);
          return;
        }
        if (draft.trim() !== value) onCommit(draft.trim());
      }}
    />
  );
};

// A native date picker that looks like the resting text until clicked. Clicking
// opens the calendar (showPicker) and a selection commits immediately. `value` and
// the committed string are ISO (YYYY-MM-DD); an empty selection commits "".
export const DateInput: FC<{
  value: string | null;
  ariaLabel?: string;
  onCommit: (value: string) => void;
}> = ({ value, ariaLabel, onCommit }) => {
  const iso = value ?? "";
  const [draft, setDraft] = useState(iso);
  useEffect(() => setDraft(iso), [iso]);
  return (
    <input
      className="cell-input cell-input--date"
      type="date"
      value={draft}
      aria-label={ariaLabel}
      style={{ textAlign: "center" }}
      onClick={(e) => {
        e.stopPropagation();
        const el = e.currentTarget as HTMLInputElement & { showPicker?: () => void };
        try {
          el.showPicker?.();
        } catch {
          /* showPicker not available — the native control still works */
        }
      }}
      onChange={(e) => {
        setDraft(e.target.value);
        if (e.target.value !== iso) onCommit(e.target.value);
      }}
    />
  );
};

// ---- The five shared columns --------------------------------------------------

export const LeadHeader: FC<{
  nameWidth: number;
  onResizeStart: (e: ReactMouseEvent) => void;
}> = ({ nameWidth, onResizeStart }) => (
  <>
    <div style={{ ...cellBase, width: WBS_W }}>WBS</div>
    <div style={{ ...cellBase, width: nameWidth, position: "relative" }}>
      Task
      <span style={resizeHandle} onMouseDown={onResizeStart} />
    </div>
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
  onCommitDays?: (value: string) => void;
  onCommitFrom?: (value: string) => void;
  onCommitTo?: (value: string) => void;
}> = ({
  nameWidth,
  wbs,
  name,
  from,
  to,
  days,
  isMilestone,
  depth = 0,
  isGroup,
  collapsed,
  onToggle,
  onCommitName,
  onCommitDays,
  onCommitFrom,
  onCommitTo,
}) => {
  const indent = 8 + depth * 14;
  const editName = !isGroup && !!onCommitName;
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
          ...cellCenter,
          width: FROM_W,
          color: "var(--text-2)",
          padding: editFrom ? 0 : undefined,
          overflow: editFrom ? "visible" : "hidden",
        }}
      >
        {editFrom ? (
          <DateInput value={fromStr} ariaLabel="Start date" onCommit={onCommitFrom!} />
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
        }}
      >
        {editTo ? (
          <DateInput value={toStr} ariaLabel="Finish date" onCommit={onCommitTo!} />
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
