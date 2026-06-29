// Change-activity table for a project: who did what, when. Reads the audit trail
// (recorded on every write) and refreshes on the same ~10s cadence as the schedule.

import { useCallback, useEffect, useState } from "react";
import { getAudit } from "../api/schedule";
import type { AuditEntry } from "../types/schedule";

const POLL_MS = 10000;

function when(iso: string): string {
  const d = new Date(iso.endsWith("Z") ? iso : `${iso}Z`); // backend stores UTC
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function ActivityPage({ projectId }: { projectId: number }) {
  const [rows, setRows] = useState<AuditEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setRows(await getAudit(projectId));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load activity");
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    void load();
    const id = window.setInterval(() => void load(), POLL_MS);
    const onFocus = () => void load();
    window.addEventListener("focus", onFocus);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("focus", onFocus);
    };
  }, [load]);

  if (loading) return <p className="muted">Loading…</p>;

  return (
    <div className="activity-page">
      {error && <div className="error-banner">{error}</div>}
      {rows.length === 0 ? (
        <p className="muted">No changes recorded yet.</p>
      ) : (
        <table className="admin-table activity-table">
          <thead>
            <tr>
              <th>When</th>
              <th>Who</th>
              <th>Action</th>
              <th>Change</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="muted nowrap">{when(r.created_at)}</td>
                <td className="nowrap">
                  {r.actor}
                  {r.source === "chat" && (
                    <span className="via-claude" title="Changed through Claude.ai chat">
                      via Claude
                    </span>
                  )}
                </td>
                <td>
                  <span className={`act-badge act-${r.action}`}>{r.action}</span>
                </td>
                <td>
                  {r.summary ??
                    `${r.action} ${r.entity_type}${r.entity_id ? ` #${r.entity_id}` : ""}`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
