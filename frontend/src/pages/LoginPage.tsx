import { useState } from "react";
import type { FormEvent } from "react";

export function LoginPage({
  onLogin,
}: {
  onLogin: (email: string, password: string) => Promise<void>;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onLogin(email.trim(), password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="splash">
      <form className="login-card" onSubmit={submit}>
        <span className="brand-mark" />
        <h1 className="login-title">RISE Schedule Hub</h1>
        <p className="login-sub">Sign in to continue</p>
        {error && <div className="error-banner">{error}</div>}
        <label className="login-field">
          <span>Email</span>
          <input
            type="email"
            value={email}
            autoFocus
            autoComplete="username"
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label className="login-field">
          <span>Password</span>
          <input
            type="password"
            value={password}
            autoComplete="current-password"
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button className="btn-primary login-btn" type="submit" disabled={busy || !email || !password}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
