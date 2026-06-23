// Read-only cross-project leadership dashboard.

import { useEffect, useState } from "react";
import { getLeadershipDigest, LeadershipDigest } from "../api/schedule";

export function DashboardPage() {
  const [digest, setDigest] = useState<LeadershipDigest | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getLeadershipDigest()
      .then(setDigest)
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (!digest) return <p className="muted">Loading dashboard…</p>;

  const totalUnits = digest.projects.reduce((s, p) => s + (p.units ?? 0), 0);
  const totalCritical = digest.projects.reduce((s, p) => s + p.critical_count, 0);
  const totalSlipped = digest.projects.reduce((s, p) => s + p.slipped_count, 0);

  return (
    <div className="page-scroll">
      <h2>Leadership dashboard</h2>

      <div className="stat-grid">
        <Stat label="Active projects" value={digest.projects.length} />
        <Stat label="Total units" value={totalUnits.toLocaleString()} />
        <Stat label="Critical tasks" value={totalCritical} />
        <Stat label="Slipped tasks" value={totalSlipped} tone={totalSlipped > 0 ? "warn" : undefined} />
      </div>

      <table className="task-table">
        <thead>
          <tr>
            <th>Project</th>
            <th>Stage</th>
            <th>Units</th>
            <th>Start</th>
            <th>Finish</th>
            <th>Tasks</th>
            <th>Critical</th>
            <th>Avg %</th>
            <th>Slipped</th>
          </tr>
        </thead>
        <tbody>
          {digest.projects.map((p) => (
            <tr key={p.project_id}>
              <td>{p.name}</td>
              <td>{p.stage}</td>
              <td>{p.units}</td>
              <td>{p.planned_start}</td>
              <td>{p.planned_finish}</td>
              <td>{p.task_count}</td>
              <td>{p.critical_count}</td>
              <td>{p.percent_complete}%</td>
              <td className={p.slipped_count > 0 ? "negative" : ""}>
                {p.slipped_count}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | string;
  tone?: "warn";
}) {
  return (
    <div className="stat-card">
      <div className={`stat-value ${tone === "warn" ? "negative" : ""}`}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
