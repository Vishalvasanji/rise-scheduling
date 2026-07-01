// Shown before a date/duration change is applied (a Gantt drag/resize or a Tasks-grid
// date/duration edit). The user confirms the specific change before anything is written;
// cancelling reverts the source input.

export function ConfirmChangeDialog({
  taskName,
  lines,
  busy,
  onConfirm,
  onCancel,
}: {
  taskName: string;
  lines: string[]; // e.g. ["Start 6/29 → 6/30", "Duration 5 → 8 days"]
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3 className="modal-title">Confirm change</h3>
        <p className="modal-body">
          Apply this change to <strong>{taskName}</strong>?
        </p>
        <ul className="modal-changes">
          {lines.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
        <div className="modal-actions">
          <button className="btn-ghost" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button className="btn-primary" onClick={onConfirm} disabled={busy}>
            {busy ? "Applying…" : "Confirm change"}
          </button>
        </div>
      </div>
    </div>
  );
}
