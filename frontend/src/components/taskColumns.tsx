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

export const LeadCells: FC<{
  nameWidth: number;
  wbs: string;
  name: string;
  from: string | Date | null;
  to: string | Date | null;
  days: number;
  isMilestone: boolean;
}> = ({ nameWidth, wbs, name, from, to, days, isMilestone }) => (
  <>
    <div style={{ ...cellBase, width: WBS_W, color: "var(--text-3)" }}>{wbs}</div>
    <div style={{ ...cellBase, width: nameWidth }} title={name}>
      {isMilestone ? "◆ " : ""}
      {name}
    </div>
    <div style={{ ...cellCenter, width: FROM_W, color: "var(--text-2)" }}>
      {from ? mmddyy(from) : "—"}
    </div>
    <div style={{ ...cellCenter, width: TO_W, color: "var(--text-2)" }}>
      {to ? mmddyy(to) : "—"}
    </div>
    <div style={{ ...cellCenter, width: DAYS_W, color: "var(--text-2)" }}>
      {isMilestone || !days ? "—" : days}
    </div>
  </>
);
