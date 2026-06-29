// Shown when a save hit a version conflict: someone else changed the task first.
// Confirm overwrites their change; Cancel keeps theirs (the grid has refreshed).

function timeAgo(iso: string | null): string {
  if (!iso) return "just now";
  const then = new Date(iso).getTime();
  const secs = Math.max(0, Math.round((Date.now() - then) / 1000));
  if (secs < 45) return "just now";
  const mins = Math.round(secs / 60);
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} hr ago`;
  return `${Math.round(hrs / 24)} d ago`;
}

export function ConflictDialog({
  taskName,
  updatedBy,
  updatedAt,
  busy,
  onConfirm,
  onCancel,
}: {
  taskName: string;
  updatedBy: string | null;
  updatedAt: string | null;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3 className="modal-title">This task changed</h3>
        <p className="modal-body">
          <strong>{taskName}</strong> was changed by{" "}
          <strong>{updatedBy || "someone"}</strong> {timeAgo(updatedAt)}. The schedule
          has been refreshed to their version.
        </p>
        <p className="modal-body">Overwrite their change with yours?</p>
        <div className="modal-actions">
          <button className="btn-ghost" onClick={onCancel} disabled={busy}>
            Keep theirs
          </button>
          <button className="btn-primary" onClick={onConfirm} disabled={busy}>
            {busy ? "Overwriting…" : "Overwrite"}
          </button>
        </div>
      </div>
    </div>
  );
}
