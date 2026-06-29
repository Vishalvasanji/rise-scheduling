// Auth gate: resolves the signed-in user from the stored token via /auth/me.
// While loading we show a splash; with no/expired token we show the login screen.

import { useCallback, useEffect, useState } from "react";
import { getMe, hasToken, login as apiLogin, logout as apiLogout, type Me } from "../api/auth";

type Status = "loading" | "in" | "out";

export function useAuth() {
  const [user, setUser] = useState<Me | null>(null);
  const [status, setStatus] = useState<Status>("loading");

  const load = useCallback(async () => {
    if (!hasToken()) {
      setUser(null);
      setStatus("out");
      return;
    }
    try {
      setUser(await getMe());
      setStatus("in");
    } catch {
      apiLogout(); // token missing/expired/invalid → back to login
      setUser(null);
      setStatus("out");
    }
  }, []);

  useEffect(() => {
    void load();
    const onFocus = () => void load();
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [load]);

  const login = useCallback(
    async (email: string, password: string) => {
      await apiLogin(email, password);
      await load();
    },
    [load],
  );

  const logout = useCallback(() => {
    apiLogout();
    setUser(null);
    setStatus("out");
  }, []);

  return { user, status, login, logout, reload: load };
}
