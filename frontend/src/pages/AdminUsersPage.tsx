import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import {
  createUser,
  deleteUser,
  listUsers,
  setUserProjects,
  updateUser,
  type UserRow,
} from "../api/users";
import { listProjects } from "../api/schedule";
import type { ProjectOut } from "../types/schedule";

export function AdminUsersPage({ currentEmail }: { currentEmail: string }) {
  const [users, setUsers] = useState<UserRow[]>([]);
  const [projects, setProjects] = useState<ProjectOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const [u, p] = await Promise.all([listUsers(), listProjects()]);
      setUsers(u);
      setProjects(p);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const projectName = useMemo(() => {
    const m = new Map(projects.map((p) => [p.id, p.name]));
    return (id: number) => m.get(id) ?? `#${id}`;
  }, [projects]);

  const run = useCallback(
    async (fn: () => Promise<unknown>) => {
      try {
        await fn();
        await refresh();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Action failed");
      }
    },
    [refresh],
  );

  if (loading) return <p className="muted">Loading…</p>;

  return (
    <div className="admin-page">
      {error && <div className="error-banner">{error}</div>}

      <AddUserForm projects={projects} onCreate={(body) => run(() => createUser(body))} />

      <div className="admin-section">
        <h2 className="admin-h2">Users</h2>
        <table className="admin-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Projects</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <UserRowEditor
                key={u.id}
                user={u}
                projects={projects}
                projectName={projectName}
                isSelf={u.email === currentEmail}
                onSetProjects={(ids) => run(() => setUserProjects(u.id, ids))}
                onResetPassword={(pw) => run(() => updateUser(u.id, { password: pw }))}
                onSetRole={(role) => run(() => updateUser(u.id, { role }))}
                onDelete={() => run(() => deleteUser(u.id))}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AddUserForm({
  projects,
  onCreate,
}: {
  projects: ProjectOut[];
  onCreate: (body: {
    email: string;
    password: string;
    full_name: string;
    role: string;
    project_ids: number[];
  }) => void;
}) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("member");
  const [ids, setIds] = useState<Set<number>>(new Set());

  const toggle = (id: number) =>
    setIds((cur) => {
      const next = new Set(cur);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    onCreate({
      email: email.trim(),
      password,
      full_name: fullName.trim(),
      role,
      project_ids: [...ids],
    });
    setEmail("");
    setFullName("");
    setPassword("");
    setRole("member");
    setIds(new Set());
  };

  return (
    <form className="admin-section admin-add" onSubmit={submit}>
      <h2 className="admin-h2">Add user</h2>
      <div className="admin-add__row">
        <input placeholder="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
        <input placeholder="Temp password" type="text" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <select value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="member">member</option>
          <option value="admin">admin</option>
        </select>
        <button className="btn-primary" type="submit" disabled={!email || !password}>
          Add
        </button>
      </div>
      {role !== "admin" && (
        <ProjectChecklist projects={projects} selected={ids} onToggle={toggle} hint="Assign projects:" />
      )}
    </form>
  );
}

function UserRowEditor({
  user,
  projects,
  projectName,
  isSelf,
  onSetProjects,
  onResetPassword,
  onSetRole,
  onDelete,
}: {
  user: UserRow;
  projects: ProjectOut[];
  projectName: (id: number) => string;
  isSelf: boolean;
  onSetProjects: (ids: number[]) => void;
  onResetPassword: (pw: string) => void;
  onSetRole: (role: string) => void;
  onDelete: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [ids, setIds] = useState<Set<number>>(new Set(user.project_ids));
  const isAdmin = user.role === "admin";

  const toggle = (id: number) =>
    setIds((cur) => {
      const next = new Set(cur);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  return (
    <tr>
      <td>{user.full_name || "—"}</td>
      <td>{user.email}</td>
      <td>
        <select
          value={user.role}
          disabled={isSelf}
          onChange={(e) => onSetRole(e.target.value)}
        >
          <option value="member">member</option>
          <option value="admin">admin</option>
        </select>
      </td>
      <td>
        {isAdmin ? (
          <span className="muted">all (admin)</span>
        ) : editing ? (
          <ProjectChecklist projects={projects} selected={ids} onToggle={toggle} />
        ) : user.project_ids.length ? (
          user.project_ids.map(projectName).join(", ")
        ) : (
          <span className="muted">none</span>
        )}
      </td>
      <td className="admin-actions">
        {!isAdmin &&
          (editing ? (
            <>
              <button
                className="btn-ghost"
                onClick={() => {
                  onSetProjects([...ids]);
                  setEditing(false);
                }}
              >
                Save
              </button>
              <button className="btn-ghost" onClick={() => setEditing(false)}>
                Cancel
              </button>
            </>
          ) : (
            <button className="btn-ghost" onClick={() => setEditing(true)}>
              Edit access
            </button>
          ))}
        <button
          className="btn-ghost"
          onClick={() => {
            const pw = window.prompt(`New password for ${user.email}:`);
            if (pw) onResetPassword(pw);
          }}
        >
          Reset password
        </button>
        {!isSelf && (
          <button
            className="btn-ghost danger"
            onClick={() => {
              if (window.confirm(`Delete ${user.email}?`)) onDelete();
            }}
          >
            Delete
          </button>
        )}
      </td>
    </tr>
  );
}

function ProjectChecklist({
  projects,
  selected,
  onToggle,
  hint,
}: {
  projects: ProjectOut[];
  selected: Set<number>;
  onToggle: (id: number) => void;
  hint?: string;
}) {
  return (
    <div className="project-checklist">
      {hint && <span className="muted">{hint}</span>}
      {projects.map((p) => (
        <label key={p.id} className="project-check">
          <input type="checkbox" checked={selected.has(p.id)} onChange={() => onToggle(p.id)} />
          {p.name}
        </label>
      ))}
    </div>
  );
}
