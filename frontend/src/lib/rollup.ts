// Derive WBS roll-up (summary) rows from a flat task list. The WBS encodes
// phase -> building -> task (e.g. "D.3.1"); every proper prefix ("D", "D.3") is a
// summary group spanning its descendant leaf tasks. This mirrors the backend's
// compute_summary_rows (date span), and additionally rolls up a duration-weighted
// % complete and an "is any child critical" flag. Frontend-only; no schema change.

import type { TaskOut } from "../types/schedule";
import { businessDays } from "./dates";

interface RowBase {
  id: string;
  code: string; // WBS code (group prefix, or the task's own wbs)
  name: string;
  depth: number;
  parentId: string | null; // immediate parent group id, for collapse
}

export interface GroupRow extends RowBase {
  kind: "group";
  start: string | null;
  finish: string | null;
  days: number;
  percent: number;
  isCritical: boolean;
  count: number;
}

export interface TaskRow extends RowBase {
  kind: "task";
  task: TaskOut;
}

export type Row = GroupRow | TaskRow;

// Natural WBS compare so "A.2" < "A.10" (segment-wise, numeric when both numeric).
function cmpWbs(a: string, b: string): number {
  const pa = a.split(".");
  const pb = b.split(".");
  const n = Math.min(pa.length, pb.length);
  for (let i = 0; i < n; i++) {
    const na = Number(pa[i]);
    const nb = Number(pb[i]);
    const bothNum = pa[i] !== "" && pb[i] !== "" && !Number.isNaN(na) && !Number.isNaN(nb);
    const c = bothNum ? na - nb : pa[i] < pb[i] ? -1 : pa[i] > pb[i] ? 1 : 0;
    if (c !== 0) return c;
  }
  return pa.length - pb.length;
}

export function buildRows(tasks: TaskOut[], labels?: Record<string, string> | null): Row[] {
  const withWbs = tasks.filter((t) => t.wbs && t.wbs.trim() !== "");
  const ungrouped = tasks.filter((t) => !t.wbs || t.wbs.trim() === "");

  // Group keys = every proper prefix of a task's WBS.
  const groupKeys = new Set<string>();
  for (const t of withWbs) {
    const seg = t.wbs!.split(".");
    for (let i = 1; i < seg.length; i++) groupKeys.add(seg.slice(0, i).join("."));
  }

  // Children buckets keyed by parent group code ("" = root).
  type Node = { code: string; group: boolean; task?: TaskOut };
  const children = new Map<string, Node[]>();
  const push = (parent: string | null, node: Node) => {
    const k = parent ?? "";
    const list = children.get(k) ?? children.set(k, []).get(k)!;
    list.push(node);
  };

  // Deepest existing group key that is a prefix of `code` (proper for groups,
  // prefix-or-self for leaves so a literal "D.3" task nests under group "D.3").
  const deepestGroup = (code: string, allowSelf: boolean): string | null => {
    const seg = code.split(".");
    for (let i = allowSelf ? seg.length : seg.length - 1; i >= 1; i--) {
      const pre = seg.slice(0, i).join(".");
      if (groupKeys.has(pre)) return pre;
    }
    return null;
  };

  for (const g of groupKeys) push(deepestGroup(g, false), { code: g, group: true });
  for (const t of withWbs) push(deepestGroup(t.wbs!, true), { code: t.wbs!, group: false, task: t });

  // Roll-up aggregation over a group's dated descendant leaves.
  const agg = (code: string): Omit<GroupRow, keyof RowBase | "kind"> => {
    const members = withWbs.filter((t) => t.wbs === code || t.wbs!.startsWith(code + "."));
    let start: string | null = null;
    let finish: string | null = null;
    let wSum = 0;
    let wDur = 0;
    let critical = false;
    for (const t of members) {
      if (t.is_critical) critical = true;
      if (t.planned_start && (start === null || t.planned_start < start)) start = t.planned_start;
      if (t.planned_finish && (finish === null || t.planned_finish > finish)) finish = t.planned_finish;
      wDur += t.duration_days;
      wSum += t.duration_days * t.percent_complete;
    }
    const percent =
      wDur > 0
        ? wSum / wDur
        : members.length
          ? members.reduce((s, t) => s + t.percent_complete, 0) / members.length
          : 0;
    const days = start && finish ? businessDays(start, finish) : 0;
    return { start, finish, days, percent, isCritical: critical, count: members.length };
  };

  const rows: Row[] = [];
  const walk = (parentKey: string, parentId: string | null, depth: number) => {
    const kids = (children.get(parentKey) ?? []).slice().sort((a, b) => cmpWbs(a.code, b.code));
    for (const node of kids) {
      if (node.group) {
        const id = "g:" + node.code;
        const name = labels?.[node.code] ?? node.code;
        rows.push({ kind: "group", id, code: node.code, name, depth, parentId, ...agg(node.code) });
        walk(node.code, id, depth + 1);
      } else {
        const t = node.task!;
        rows.push({ kind: "task", id: String(t.id), code: t.wbs!, name: t.name, depth, parentId, task: t });
      }
    }
  };
  walk("", null, 0);

  // Tasks with no WBS render flat at the end.
  for (const t of ungrouped) {
    rows.push({ kind: "task", id: String(t.id), code: "", name: t.name, depth: 0, parentId: null, task: t });
  }

  return rows;
}

// Rows whose every ancestor group is expanded (collapsed = set of group ids).
export function visibleRows(rows: Row[], collapsed: Set<string>): Row[] {
  const parentById = new Map(rows.map((r) => [r.id, r.parentId] as const));
  const hidden = (r: Row): boolean => {
    let p = r.parentId;
    while (p) {
      if (collapsed.has(p)) return true;
      p = parentById.get(p) ?? null;
    }
    return false;
  };
  return rows.filter((r) => !hidden(r));
}
