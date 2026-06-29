// "Connect Claude" panel: mints the signed-in user's personal long-lived connector
// token and shows the MCP URL + token to paste into a Claude.ai custom connector.
// Chat changes made through that connector are attributed to this user and scoped to
// the projects they're assigned — same access rules as the web app.

import { useState } from "react";
import { getConnectorToken, type ConnectorToken } from "../api/auth";

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
  const [creds, setCreds] = useState<ConnectorToken | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generate = async () => {
    setBusy(true);
    setError(null);
    try {
      setCreds(await getConnectorToken());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't generate a token");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="connect-page">
      <div className="state-card connect-card">
        <h2>Connect Claude</h2>
        <p className="muted">
          Use the RISE schedule from Claude.ai chat. Generate your personal connector
          token, then add it as a custom connector in Claude. Anything you change through
          chat is recorded under your name and limited to the projects you're assigned.
        </p>

        {!creds ? (
          <button className="btn" type="button" onClick={generate} disabled={busy}>
            {busy ? "Generating…" : "Generate connector token"}
          </button>
        ) : (
          <>
            <CopyField label="Connector URL" value={creds.connector_url} />
            <CopyField label="Bearer token" value={creds.token} />
            <p className="connect-warning">
              This token grants your access — keep it private. Generating a new one is how
              you rotate it.
            </p>
            <button className="btn-ghost" type="button" onClick={generate} disabled={busy}>
              {busy ? "Generating…" : "Regenerate"}
            </button>
          </>
        )}

        {error && <div className="error-banner">{error}</div>}

        <ol className="connect-steps">
          <li>In Claude.ai, open <strong>Settings → Connectors → Add custom connector</strong>.</li>
          <li>Paste the <strong>Connector URL</strong> above as the remote MCP server URL.</li>
          <li>Choose <strong>Bearer token</strong> authentication and paste your token.</li>
          <li>Save, then start a chat and ask about your schedule.</li>
        </ol>
      </div>
    </div>
  );
}
