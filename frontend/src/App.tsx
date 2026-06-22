import { useCallback, useEffect, useState } from "react";
import { listProjects } from "./api/schedule";
import type { ProjectOut } from "./types/schedule";
import { ProjectPage } from "./pages/ProjectPage";
import { DashboardPage } from "./pages/DashboardPage";
import "./styles.css";

type Selection = number | "dashboard";

export default function App() {
  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [selected, setSelected] = useState<Selection | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setStatus("loading");
    listProjects()
      .then((ps) => {
        setProjects(ps);
        setSelected((cur) => cur ?? (ps.length ? ps[0].id : "dashboard"));
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
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" />
          <span className="brand-name">RISE Schedule Hub</span>
        </div>
        <nav className="nav">
          <button
            className={`nav-item ${selected === "dashboard" ? "is-active" : ""}`}
            onClick={() => setSelected("dashboard")}
          >
            <span className="nav-item__name">Leadership dashboard</span>
          </button>
          <div className="nav-section">Projects</div>
          {projects.map((p) => (
            <button
              key={p.id}
              className={`nav-item ${selected === p.id ? "is-active" : ""}`}
              onClick={() => setSelected(p.id)}
            >
              <span className="nav-item__name">{p.name}</span>
              <span className="nav-item__stage">{p.stage}</span>
            </button>
          ))}
        </nav>
      </aside>
      <main className="content">
        {selected === "dashboard" && <DashboardPage />}
        {typeof selected === "number" && <ProjectPage projectId={selected} />}
      </main>
    </div>
  );
}
