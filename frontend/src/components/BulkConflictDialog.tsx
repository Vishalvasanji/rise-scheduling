// Shown when a batched "Save all" hit rows that changed underneath since the edit
// session began. Lists the affected tasks; Overwrite forces the whole batch,
// Cancel keeps editing (the schedule has refreshed to the latest).

import type { BulkConflict } from "../hooks/useSchedule";

function timeAgo(iso: string | null): string {
  if (!iso) return "just now";
  const secs = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
  if (secs < 45) return "just now";
  const mins = Math.round(secs / 60);
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} hr ago`;
  return `${Math.round(hrs / 24)} d ago`;
}

export function BulkConflictDialog({
  conflicts,
  busy,
  onOverwrite,
  onCancel,
}: {
  conflicts: BulkConflict[];
  busy?: boolean;
  onOverwrite: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3 className="modal-title">
          {conflicts.length === 1 ? "A task changed" : `${conflicts.length} tasks changed`}
        </h3>
        <p className="modal-body">
          These were changed by someone else since you started editing. Nothing was saved.
        </p>
        <ul className="modal-changes">
          {conflicts.map((c) => (
            <li key={c.task_id}>
              <strong>{c.name}</strong> — {c.updated_by || "someone"} {timeAgo(c.updated_at)}
            </li>
          ))}
        </ul>
        <p className="modal-body">Overwrite their changes with your edits?</p>
        <div className="modal-actions">
          <button className="btn-ghost" onClick={onCancel} disabled={busy}>
            Keep editing
          </button>
          <button className="btn-primary" onClick={onOverwrite} disabled={busy}>
            {busy ? "Overwriting…" : "Overwrite & save"}
          </button>
        </div>
      </div>
    </div>
  );
}
