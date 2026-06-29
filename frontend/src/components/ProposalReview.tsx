// Banner + collapsible diff panel for a pending "what-if" proposal (staged from
// Claude chat or the API). "Review" toggles the schedule into review mode where
// the Gantt/grid render the *proposed* schedule with changed tasks color-coded;
// Apply commits it for real, Discard clears it. The diff panel lists each task's
// before → after plus the project-finish delta so the change is legible without
// hunting across bars.

import { useState } from "react";
import type { ProposalOut, TaskChange } from "../types/schedule";
import { mmddyy } from "../lib/dates";

interface Props {
  proposal: ProposalOut;
  reviewing: boolean;
  busy: boolean;
  liveFinish: string | null;
  onToggleReview: () => void;
  onApply: () => void;
  onDiscard: () => void;
  onUndoLast: () => void;
}

const LABEL: Record<TaskChange["change_type"], string> = {
  new: "New",
  removed: "Removed",
  moved: "Moved",
  modified: "Modified",
};

function changeDetail(c: TaskChange): string {
  if (c.change_type === "new") {
    return c.proposed?.planned_start
      ? `${mmddyy(c.proposed.planned_start)} → ${mmddyy(c.proposed.planned_finish!)}`
      : "added";
  }
  if (c.change_type === "removed") return "deleted";
  const cur = c.current;
  const prop = c.proposed;
  if (
    cur?.planned_finish &&
    prop?.planned_finish &&
    (cur.planned_finish !== prop.planned_finish || cur.planned_start !== prop.planned_start)
  ) {
    return `${mmddyy(cur.planned_finish)} → ${mmddyy(prop.planned_finish)}`;
  }
  if (cur && prop && cur.duration_days !== prop.duration_days) {
    return `${cur.duration_days}d → ${prop.duration_days}d`;
  }
  return "updated";
}

function finishDelta(live: string | null, proposed: string | null): string | null {
  if (!proposed || !live) return null;
  if (proposed === live) return "Project finish unchanged";
  const dir = proposed > live ? "later" : "earlier";
  return `Project finish ${mmddyy(live)} → ${mmddyy(proposed)} (${dir})`;
}

export function ProposalReview({
  proposal,
  reviewing,
  busy,
  liveFinish,
  onToggleReview,
  onApply,
  onDiscard,
  onUndoLast,
}: Props) {
  const [open, setOpen] = useState(true);
  const count = proposal.changes.length;
  const steps = proposal.steps ?? [];
  const delta = finishDelta(liveFinish, proposal.schedule.project.planned_finish);

  return (
    <div className={`proposal-banner${reviewing ? " reviewing" : ""}`}>
      <div className="proposal-banner__bar">
        <span className="proposal-banner__dot" />
        <div className="proposal-banner__text">
          <strong>Proposed changes</strong>
          {proposal.summary ? <span> — {proposal.summary}</span> : null}
          <span className="proposal-banner__meta">
            {" "}
            {steps.length > 1 ? `${steps.length} steps · ` : ""}
            {count} {count === 1 ? "change" : "changes"}
            {proposal.actor ? ` · from ${proposal.actor}` : ""}
          </span>
        </div>
        <div className="proposal-banner__actions">
          <button onClick={() => setOpen((v) => !v)} className="btn-ghost">
            {open ? "Hide details" : "Details"}
          </button>
          <button onClick={onToggleReview} className={reviewing ? "btn-ghost active" : "btn-ghost"}>
            {reviewing ? "Exit review" : "Review"}
          </button>
          {steps.length > 0 && (
            <button onClick={onUndoLast} disabled={busy} className="btn-ghost">
              Undo last
            </button>
          )}
          <button onClick={onDiscard} disabled={busy} className="btn-ghost danger">
            Discard all
          </button>
          <button onClick={onApply} disabled={busy} className="btn-primary">
            {busy ? "Applying…" : "Apply"}
          </button>
        </div>
      </div>

      {open && (
        <div className="diff-panel">
          {steps.length > 0 && (
            <ol className="step-list">
              {steps.map((s, i) => (
                <li key={i} className={`step-row${i === steps.length - 1 ? " step-row--last" : ""}`}>
                  <span className="step-num">{i + 1}</span>
                  <span className="step-summary">{s.summary ?? "Change"}</span>
                  {s.change_count ? (
                    <span className="step-count">
                      {s.change_count} {s.change_count === 1 ? "edit" : "edits"}
                    </span>
                  ) : null}
                </li>
              ))}
            </ol>
          )}
          {delta && <div className="diff-panel__finish">{delta}</div>}
          <ul className="diff-list">
            {proposal.changes.map((c) => (
              <li key={`${c.change_type}-${c.task_id}`} className={`diff-row diff-row--${c.change_type}`}>
                <span className={`diff-tag diff-tag--${c.change_type}`}>{LABEL[c.change_type]}</span>
                <span className="diff-name">{c.name}</span>
                <span className="diff-detail">{changeDetail(c)}</span>
              </li>
            ))}
            {count === 0 && <li className="diff-row muted">No net change to the schedule.</li>}
          </ul>
        </div>
      )}
    </div>
  );
}
