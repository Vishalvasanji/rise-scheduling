import { useCallback, useEffect, useState } from "react";
import { listProjects } from "./api/schedule";
import type { ProjectOut } from "./types/schedule";
import { getClaudeStatus, type Me } from "./api/auth";
import { ProjectPage } from "./pages/ProjectPage";
import { ActivityPage } from "./pages/ActivityPage";
import { LoginPage } from "./pages/LoginPage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { ConnectClaudePage } from "./pages/ConnectClaudePage";
import { useAuth } from "./hooks/useAuth";
import "./styles.css";

export default function App() {
  const { user, status, waking, login, logout } = useAuth();

  if (status === "loading") {
    return (
      <div className="splash">
        <div className="spinner" />
        <p className="splash-text">
          {waking
            ? "Waking up the server — this can take a minute…"
            : "Loading RISE Schedule Hub…"}
        </p>
      </div>
    );
  }

  if (status === "out" || !user) {
    return <LoginPage onLogin={login} />;
  }

  return <AuthedApp user={user} onLogout={logout} />;
}

function AuthedApp({ user, onLogout }: { user: Me; onLogout: () => void }) {
  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [tab, setTab] = useState<"gantt" | "grid" | "activity">("gantt");
  const [view, setView] = useState<"project" | "admin" | "connect">("project");
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [claudeConnected, setClaudeConnected] = useState<boolean | null>(null);

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

  // Claude connection status for the header pill. Connecting happens externally in
  // Claude.ai, so poll (and refresh on focus / when returning to the schedule view).
  const refreshClaude = useCallback(() => {
    getClaudeStatus()
      .then((r) => setClaudeConnected(r.connected))
      .catch(() => {});
  }, []);

  useEffect(() => {
    refreshClaude();
    const id = window.setInterval(refreshClaude, 60000);
    const onFocus = () => refreshClaude();
    window.addEventListener("focus", onFocus);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("focus", onFocus);
    };
  }, [refreshClaude]);

  useEffect(() => {
    if (view === "project") refreshClaude();
  }, [view, refreshClaude]);

  const userLabel = user.full_name || user.email;

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand-mark" />
        <span className="brand-name">RISE Schedule Hub</span>

        {view === "project" && (
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
        )}

        <nav className="top-nav">
          {view === "project" ? (
            selected != null && (
              <>
                <button
                  className={`top-nav__item${tab === "gantt" ? " active" : ""}`}
                  onClick={() => setTab("gantt")}
                >
                  Schedule
                </button>
                <button
                  className={`top-nav__item${tab === "grid" ? " active" : ""}`}
                  onClick={() => setTab("grid")}
                >
                  Tasks
                </button>
                <button
                  className={`top-nav__item${tab === "activity" ? " active" : ""}`}
                  onClick={() => setTab("activity")}
                >
                  Activity
                </button>
              </>
            )
          ) : (
            <button className="top-nav__item" onClick={() => setView("project")}>
              ← Back to schedule
            </button>
          )}
        </nav>

        <div className="topbar__spacer" />

        <div className="topbar__user">
          {view === "project" && (
            <button
              className={`claude-pill ${
                claudeConnected == null
                  ? "claude-pill--unknown"
                  : claudeConnected
                    ? "claude-pill--live"
                    : "claude-pill--down"
              }`}
              onClick={() => setView("connect")}
              title={
                claudeConnected
                  ? "Claude connected — click to manage"
                  : "Claude not connected — click to set up"
              }
            >
              <span className="claude-pill__dot" />
              Claude
            </button>
          )}
          {user.is_admin && view === "project" && (
            <button className="top-nav__item" onClick={() => setView("admin")}>
              Users
            </button>
          )}
          <span className="user-chip" title={user.email}>
            {userLabel}
          </span>
          <button className="btn-ghost" onClick={onLogout}>
            Log out
          </button>
        </div>
      </header>

      <main className="content">
        {view === "connect" ? (
          <ConnectClaudePage />
        ) : view === "admin" ? (
          <AdminUsersPage currentEmail={user.email} />
        ) : status === "loading" ? (
          <p className="muted">Loading…</p>
        ) : status === "error" ? (
          <div className="state-card">
            <h2>Couldn’t reach the schedule</h2>
            <p className="muted">{error}</p>
            <button className="btn" onClick={load}>
              Try again
            </button>
          </div>
        ) : selected != null ? (
          tab === "activity" ? (
            <ActivityPage key={`act-${selected}`} projectId={selected} />
          ) : (
            <ProjectPage key={selected} projectId={selected} tab={tab} />
          )
        ) : (
          <p className="muted">
            No projects assigned yet
            {user.is_admin ? "." : " — ask your admin for access."}
          </p>
        )}
      </main>
    </div>
  );
}
