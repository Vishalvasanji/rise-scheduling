import { useEffect, useState } from "react";
import { listProjects } from "./api/schedule";
import type { ProjectOut } from "./types/schedule";
import { ProjectPage } from "./pages/ProjectPage";
import { DashboardPage } from "./pages/DashboardPage";
import "./styles.css";

export default function App() {
  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [selected, setSelected] = useState<number | "dashboard" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProjects()
      .then((ps) => {
        setProjects(ps);
        setSelected(ps.length ? ps[0].id : "dashboard");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load projects"));
  }, []);

  return (
    <div className="app">
      <aside className="sidebar">
        <h1>RISE Schedule Hub</h1>
        <nav>
          <button
            className={selected === "dashboard" ? "active" : ""}
            onClick={() => setSelected("dashboard")}
          >
            ▦ Leadership dashboard
          </button>
          <div className="nav-section">Projects</div>
          {projects.map((p) => (
            <button
              key={p.id}
              className={selected === p.id ? "active" : ""}
              onClick={() => setSelected(p.id)}
            >
              {p.name}
              <span className="nav-stage">{p.stage}</span>
            </button>
          ))}
        </nav>
      </aside>
      <main className="content">
        {error && <div className="error-banner">{error}</div>}
        {selected === "dashboard" && <DashboardPage />}
        {typeof selected === "number" && <ProjectPage projectId={selected} />}
      </main>
    </div>
  );
}
