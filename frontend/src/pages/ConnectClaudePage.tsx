// "Connect Claude" panel: shows the MCP connector URL to paste into Claude.ai, with
// step-by-step instructions. Claude runs an OAuth flow against the URL and the user signs
// in with their scheduling-hub account, so chat changes are recorded under their name and
// limited to the projects they're assigned — no token to copy or store.

import { useCallback, useEffect, useState } from "react";
import { getConnectorUrl, warmConnector } from "../api/auth";

type WarmState = "waking" | "ready" | "down";

// The connector server is a free-tier service that sleeps when idle, so the first
// connection from Claude can time out. Ping it (via our API) when this page opens so
// it's awake by the time the user clicks Connect, and let them re-wake it on demand.
function ServerStatus() {
  const [state, setState] = useState<WarmState>("waking");

  const wake = useCallback(() => {
    setState("waking");
    warmConnector()
      .then((r) => setState(r.ready ? "ready" : "down"))
      .catch(() => setState("down"));
  }, []);

  useEffect(() => {
    wake();
  }, [wake]);

  return (
    <div className={`server-status server-status--${state}`}>
      <span className="server-status__dot" />
      {state === "waking" && (
        <span>Waking up the schedule server… (this can take up to a minute)</span>
      )}
      {state === "ready" && (
        <span>
          <strong>Server ready</strong> — connect now while it's awake.
        </span>
      )}
      {state === "down" && (
        <span>
          Couldn't reach the server.{" "}
          <button className="server-status__retry" type="button" onClick={wake}>
            Wake server
          </button>
        </span>
      )}
    </div>
  );
}

function ConnectorUrl({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable — the URL is fully shown and selectable as a fallback */
    }
  };
  return (
    <div className="connect-url">
      <div className="connect-url__label">Connector URL</div>
      <code className="connect-url__value">{value}</code>
      <button className="btn connect-url__copy" type="button" onClick={copy}>
        {copied ? "Copied ✓" : "Copy URL"}
      </button>
    </div>
  );
}

export function ConnectClaudePage() {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getConnectorUrl()
      .then((r) => setUrl(r.connector_url))
      .catch((e) => setError(e instanceof Error ? e.message : "Couldn't load the connector URL"));
  }, []);

  return (
    <div className="connect-page">
      <div className="connect-card">
        <h2>Connect Claude to your schedule</h2>
        <p className="muted">
          Follow these steps once to use RISE from Claude chat. Anything you change through
          chat is saved under your name and limited to the projects you're assigned.
        </p>

        {error && <div className="error-banner">{error}</div>}
        {url && <ConnectorUrl value={url} />}

        <ServerStatus />

        <ol className="connect-steps">
          <li>
            Open <strong>claude.ai</strong> in your web browser and sign in to your Claude
            account.
          </li>
          <li>
            In the menu on the left, click <strong>Customize</strong>, then click{" "}
            <strong>Connectors</strong>.
          </li>
          <li>
            Next to <strong>Connectors</strong>, click the <strong>+</strong> button, then
            click <strong>Add custom connector</strong>.
          </li>
          <li>
            In the <strong>Name</strong> box, type <strong>RISE Schedule</strong> (any name
            is fine).
          </li>
          <li>
            In the <strong>Remote MCP server URL</strong> box, paste the{" "}
            <strong>Connector URL</strong> from above (use the <strong>Copy URL</strong>{" "}
            button). Leave everything under <strong>Advanced settings</strong> (the OAuth
            boxes) empty.
          </li>
          <li>
            Click <strong>Add</strong>. RISE now shows up in your connectors list.
          </li>
          <li>
            Make sure the box above says <strong>Server ready</strong> (click{" "}
            <strong>Wake server</strong> if it doesn't), then click <strong>Connect</strong>{" "}
            next to RISE. A <strong>RISE Schedule Hub sign-in</strong> window pops up.
            <br />
            <span className="muted">
              If it says it couldn't connect or that the server may be waking up, wait a few
              seconds and click <strong>Connect</strong> again — the first wake-up can be slow.
            </span>
          </li>
          <li>
            Enter the <strong>same email and password you use to sign in here</strong>, then
            click <strong>Sign in &amp; authorize</strong>.
          </li>
          <li>
            You're connected. Start a new chat in Claude and ask about your schedule — for
            example, <em>"What's happening on Lake Jackson this week?"</em>
          </li>
        </ol>

        <p className="connect-hint muted">
          Only need to do this once. To reconnect later, repeat steps 1–3 and pick RISE from
          your connectors.
        </p>
      </div>
    </div>
  );
}
