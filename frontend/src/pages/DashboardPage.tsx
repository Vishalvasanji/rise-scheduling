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

  return (
    <div>
      <h2>Leadership dashboard</h2>
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
