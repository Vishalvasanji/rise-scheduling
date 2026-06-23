import { useCallback, useEffect, useState } from "react";
import { listProjects } from "./api/schedule";
import type { ProjectOut } from "./types/schedule";
import { ProjectPage } from "./pages/ProjectPage";
import { DashboardPage } from "./pages/DashboardPage";
import "./styles.css";

type Selection = number | "dashboard";

function initials(name: string): string {
  const words = name.trim().split(/\s+/);
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

export default function App() {
  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [selected, setSelected] = useState<Selection | null>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState<boolean>(
    () => localStorage.getItem("rise_sidebar_collapsed") === "true",
  );

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

  const toggleCollapsed = () =>
    setCollapsed((v) => {
      localStorage.setItem("rise_sidebar_collapsed", String(!v));
      return !v;
    });

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
      <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
        <div className="sidebar-head">
          <span className="brand-mark" />
          <span className="brand-name">RISE Schedule Hub</span>
          <button
            className="sidebar-toggle"
            onClick={toggleCollapsed}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label="Toggle sidebar"
          >
            {collapsed ? "»" : "«"}
          </button>
        </div>
        <nav className="nav">
          <button
            className={`nav-item ${selected === "dashboard" ? "is-active" : ""}`}
            onClick={() => setSelected("dashboard")}
            title="Leadership dashboard"
          >
            <span className="nav-item__badge">▦</span>
            <span className="nav-item__text">
              <span className="nav-item__name">Leadership dashboard</span>
            </span>
          </button>
          <div className="nav-section">Projects</div>
          {projects.map((p) => (
            <button
              key={p.id}
              className={`nav-item ${selected === p.id ? "is-active" : ""}`}
              onClick={() => setSelected(p.id)}
              title={p.name}
            >
              <span className="nav-item__badge">{initials(p.name)}</span>
              <span className="nav-item__text">
                <span className="nav-item__name">{p.name}</span>
                <span className="nav-item__stage">{p.stage}</span>
              </span>
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
