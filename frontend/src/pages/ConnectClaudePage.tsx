// "Connect Claude" panel: shows the MCP connector URL to paste into Claude.ai. Claude
// runs an OAuth flow against it and the user signs in with their scheduling-hub account,
// so chat changes are recorded under their name and limited to the projects they're
// assigned — no token to copy or store.

import { useEffect, useState } from "react";
import { getConnectorUrl } from "../api/auth";

function CopyField({ label, value }: { label: string; value: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable — the field is selectable as a fallback */
    }
  };
  return (
    <div className="connect-field">
      <label className="connect-field__label">{label}</label>
      <div className="connect-field__row">
        <input className="connect-field__input" readOnly value={value} onFocus={(e) => e.target.select()} />
        <button className="btn" type="button" onClick={copy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
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
      <div className="state-card connect-card">
        <h2>Connect Claude</h2>
        <p className="muted">
          Use the RISE schedule from Claude.ai chat. Add the connector below, then sign in
          with your RISE Schedule Hub email and password when Claude prompts you. Anything
          you change through chat is recorded under your name and limited to the projects
          you're assigned.
        </p>

        {error && <div className="error-banner">{error}</div>}
        {url && <CopyField label="Connector URL" value={url} />}

        <ol className="connect-steps">
          <li>In Claude.ai, open <strong>Settings → Connectors → Add custom connector</strong>.</li>
          <li>Paste the <strong>Connector URL</strong> above as the Remote MCP server URL, and leave the OAuth fields blank.</li>
          <li>Click <strong>Add</strong> — Claude opens a RISE sign-in page.</li>
          <li>Sign in with your <strong>scheduling-hub email &amp; password</strong>, then start a chat and ask about your schedule.</li>
        </ol>
      </div>
    </div>
  );
}
