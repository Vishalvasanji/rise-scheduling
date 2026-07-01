// "Connect Claude" panel: shows the MCP connector URL to paste into Claude.ai, with
// step-by-step instructions. Claude runs an OAuth flow against the URL and the user signs
// in with their scheduling-hub account, so chat changes are recorded under their name and
// limited to the projects they're assigned — no token to copy or store.

import { useEffect, useState } from "react";
import { getConnectorUrl } from "../api/auth";

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
            Click <strong>Add</strong>. A <strong>RISE Schedule Hub sign-in</strong> window
            will pop up.
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
