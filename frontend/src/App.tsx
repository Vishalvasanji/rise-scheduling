import { useCallback, useEffect, useState } from "react";
import { listProjects } from "./api/schedule";
import type { ProjectOut } from "./types/schedule";
import { ProjectPage } from "./pages/ProjectPage";
import "./styles.css";

export default function App() {
  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setStatus("loading");
    listProjects()
      .then((ps) => {
        setProjects(ps);
        setSelected((cur) => cur ?? (ps.length ? ps[0].id : null));
        setStatus("ready");
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load projects");
        setStatus("error");
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (status === "loading") {
    return (
      <div className="splash">
        <div className="spinner" />
        <p className="splash-text">Loading RISE Schedule Hub…</p>
        <p className="splash-hint">
          The first load can take up to a minute while the server wakes from sleep.
        </p>
      </div>
    );
  }

  if (status === "error") {
    return (
      <div className="splash">
        <div className="state-card">
          <h2>Couldn’t reach the schedule</h2>
          <p className="muted">{error}</p>
          <p className="splash-hint">
            The backend may be waking from sleep — this usually clears in a moment.
          </p>
          <button className="btn" onClick={load}>
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand-mark" />
        <span className="brand-name">RISE Schedule Hub</span>
        <div className="project-picker">
          <select
            className="project-select"
            value={selected ?? ""}
            onChange={(e) => setSelected(Number(e.target.value))}
            aria-label="Select project"
          >
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </header>
      <main className="content">
        {selected != null ? (
          <ProjectPage key={selected} projectId={selected} />
        ) : (
          <p className="muted">No projects yet.</p>
        )}
      </main>
    </div>
  );
}
