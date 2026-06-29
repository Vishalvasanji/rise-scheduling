// Polls a project's single pending "what-if" proposal so the web app notices
// changes staged from Claude chat (which has no push channel). Polls every ~10s
// and on window focus. Apply commits the proposal for real; discard clears it —
// both then notify the caller so the live schedule can refetch.

import { useCallback, useEffect, useState } from "react";
import {
  applyProposal,
  discardProposal,
  getProposal,
  undoLastChange,
} from "../api/schedule";
import type { ProposalOut } from "../types/schedule";

const POLL_MS = 10000;

export function useProposal(projectId: number | null, onApplied?: () => void) {
  const [proposal, setProposal] = useState<ProposalOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (projectId == null) return;
    try {
      setProposal(await getProposal(projectId));
    } catch {
      // Polling failures are non-fatal — keep the last known state.
    }
  }, [projectId]);

  useEffect(() => {
    setProposal(null);
    void refresh();
    const id = window.setInterval(() => void refresh(), POLL_MS);
    const onFocus = () => void refresh();
    window.addEventListener("focus", onFocus);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("focus", onFocus);
    };
  }, [refresh]);

  const apply = useCallback(async () => {
    if (projectId == null) return;
    setBusy(true);
    try {
      await applyProposal(projectId);
      setProposal(null);
      setError(null);
      onApplied?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to apply the proposal");
    } finally {
      setBusy(false);
    }
  }, [projectId, onApplied]);

  const discard = useCallback(async () => {
    if (projectId == null) return;
    setBusy(true);
    try {
      await discardProposal(projectId);
      setProposal(null);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to discard the proposal");
    } finally {
      setBusy(false);
    }
  }, [projectId]);

  const undoLast = useCallback(async () => {
    if (projectId == null) return;
    setBusy(true);
    try {
      // Returns the updated proposal, or null once the last step is undone.
      setProposal(await undoLastChange(projectId));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to undo the last change");
    } finally {
      setBusy(false);
    }
  }, [projectId]);

  return { proposal, busy, error, apply, discard, undoLast, refresh };
}
