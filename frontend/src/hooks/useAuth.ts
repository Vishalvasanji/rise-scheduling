// Auth gate: resolves the signed-in user from the stored token via /auth/me.
// While loading we show a splash; with no token we show the login screen.
//
// The stored token is only discarded when the server REJECTS it (401/403).
// Any other failure — the API asleep on its free tier, booting behind the
// readiness gate (503), or a network blip — keeps the token and retries, so a
// valid 30-day session is never destroyed by a transient error.

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "../api/client";
import { getMe, hasToken, login as apiLogin, logout as apiLogout, type Me } from "../api/auth";

type Status = "loading" | "in" | "out";

const RETRY_MS = 5000;

export function useAuth() {
  const [user, setUser] = useState<Me | null>(null);
  const [status, setStatus] = useState<Status>("loading");
  // True once a load attempt failed for a non-auth reason (server waking up).
  const [waking, setWaking] = useState(false);
  const retryTimer = useRef<number | undefined>(undefined);

  const load = useCallback(async () => {
    window.clearTimeout(retryTimer.current);
    if (!hasToken()) {
      setUser(null);
      setStatus("out");
      return;
    }
    try {
      setUser(await getMe());
      setStatus("in");
      setWaking(false);
    } catch (e) {
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
        // The server saw the token and rejected it — genuinely expired/invalid.
        apiLogout();
        setUser(null);
        setStatus("out");
        setWaking(false);
        return;
      }
      // Unreachable or still starting: keep the token, stay on the splash, retry.
      setWaking(true);
      retryTimer.current = window.setTimeout(() => void load(), RETRY_MS);
    }
  }, []);

  useEffect(() => {
    void load();
    const onFocus = () => void load();
    window.addEventListener("focus", onFocus);
    return () => {
      window.removeEventListener("focus", onFocus);
      window.clearTimeout(retryTimer.current);
    };
  }, [load]);

  const login = useCallback(
    async (email: string, password: string) => {
      await apiLogin(email, password);
      await load();
    },
    [load],
  );

  const logout = useCallback(() => {
    window.clearTimeout(retryTimer.current);
    apiLogout();
    setUser(null);
    setStatus("out");
    setWaking(false);
  }, []);

  return { user, status, waking, login, logout, reload: load };
}
