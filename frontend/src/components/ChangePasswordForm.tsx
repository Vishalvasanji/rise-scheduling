// Change-password form, used two ways: as the full-screen forced gate when the
// account is on an admin-issued/seeded temp password (must_change_password), and
// as a dialog from the header's "Change password". Calls onDone after a
// successful change so the caller can refresh /auth/me.

import { useState } from "react";
import type { FormEvent } from "react";
import { changePassword } from "../api/auth";
import { ApiError } from "../api/client";

export function ChangePasswordForm({
  forced,
  onDone,
  onCancel,
}: {
  /** Forced first-login rotation: explains why, no cancel. */
  forced?: boolean;
  onDone: () => void;
  onCancel?: () => void;
}) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (next !== confirm) {
      setError("New passwords don't match.");
      return;
    }
    if (next.length < 8) {
      setError("New password must be at least 8 characters.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await changePassword(current, next);
      onDone();
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 403
          ? "Current password is incorrect."
          : err instanceof Error
            ? err.message
            : "Couldn't change the password.",
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="login-card" onSubmit={submit}>
      <span className="brand-mark" />
      <h1 className="login-title">{forced ? "Set a new password" : "Change password"}</h1>
      <p className="login-sub">
        {forced
          ? "You're using a temporary password — pick your own to continue."
          : "Enter your current password, then the new one."}
      </p>
      {error && <div className="error-banner">{error}</div>}
      <label className="login-field">
        <span>{forced ? "Temporary password" : "Current password"}</span>
        <input
          type="password"
          value={current}
          autoFocus
          autoComplete="current-password"
          onChange={(e) => setCurrent(e.target.value)}
        />
      </label>
      <label className="login-field">
        <span>New password (8+ characters)</span>
        <input
          type="password"
          value={next}
          autoComplete="new-password"
          onChange={(e) => setNext(e.target.value)}
        />
      </label>
      <label className="login-field">
        <span>Confirm new password</span>
        <input
          type="password"
          value={confirm}
          autoComplete="new-password"
          onChange={(e) => setConfirm(e.target.value)}
        />
      </label>
      <button
        className="btn-primary login-btn"
        type="submit"
        disabled={busy || !current || !next || !confirm}
      >
        {busy ? "Saving…" : forced ? "Set password" : "Change password"}
      </button>
      {!forced && onCancel && (
        <button className="btn-ghost" type="button" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
      )}
    </form>
  );
}
