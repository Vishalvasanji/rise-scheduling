"""The sign-in page for the Claude.ai connector's OAuth flow. The OAuth ``authorize``
step redirects the user here; they sign in with their scheduling-hub email/password,
and on success we mint an authorization code and redirect back to the connector."""

from __future__ import annotations

import html

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from app.auth import get_auth_backend
from app.db.session import session_scope
from app.mcp.oauth import (
    issue_code_after_login,
    redirect_after_login,
    verify_login_request,
)
from app.services import auth_service


def _page(req: str, error: str | None = None) -> str:
    err = (
        f'<p class="err">{html.escape(error)}</p>' if error else ""
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Sign in · RISE Schedule Hub</title>
<style>
  body {{ font-family: -apple-system, system-ui, sans-serif; background: #f4f4f7;
    display: flex; min-height: 100vh; align-items: center; justify-content: center;
    margin: 0; color: #1c1c1e; }}
  .card {{ background: #fff; padding: 32px; border-radius: 16px; width: 340px;
    box-shadow: 0 10px 40px rgba(0,0,0,.08); }}
  h1 {{ font-size: 18px; margin: 0 0 4px; }}
  p.sub {{ color: #6b6b70; font-size: 13px; margin: 0 0 20px; }}
  label {{ font-size: 12px; font-weight: 600; color: #6b6b70; display: block;
    margin-bottom: 4px; }}
  input {{ width: 100%; box-sizing: border-box; padding: 10px 12px; margin-bottom: 14px;
    border: 1px solid #d8d8dd; border-radius: 8px; font-size: 14px; }}
  button {{ width: 100%; padding: 11px; border: 0; border-radius: 8px; background: #2f6bff;
    color: #fff; font-size: 14px; font-weight: 600; cursor: pointer; }}
  .err {{ color: #d1293d; font-size: 13px; margin: 0 0 12px; }}
</style></head>
<body>
  <div class="card">
    <h1>Connect Claude to RISE</h1>
    <p class="sub">Sign in with your RISE Schedule Hub account to authorize Claude.</p>
    {err}
    <form method="post" action="/oauth/login">
      <input type="hidden" name="req" value="{html.escape(req)}">
      <label for="email">Email</label>
      <input id="email" name="email" type="email" autocomplete="username" required>
      <label for="password">Password</label>
      <input id="password" name="password" type="password"
        autocomplete="current-password" required>
      <button type="submit">Sign in &amp; authorize</button>
    </form>
  </div>
</body></html>"""


async def oauth_login(request: Request) -> HTMLResponse | RedirectResponse:
    if request.method == "GET":
        req = request.query_params.get("req", "")
        if not verify_login_request(req):
            return HTMLResponse(
                _page("", "This sign-in link is invalid or expired."), status_code=400
            )
        return HTMLResponse(_page(req))

    # POST: authenticate, then complete the authorization-code grant.
    form = await request.form()
    req = str(form.get("req", ""))
    email = str(form.get("email", "")).strip()
    password = str(form.get("password", ""))

    claims = verify_login_request(req)
    if not claims:
        return HTMLResponse(_page("", "This sign-in link is invalid or expired."), status_code=400)

    with session_scope() as session:
        user = auth_service.get_by_email(session, email)
        ok = user is not None and get_auth_backend().verify_password(
            password, user.password_hash
        )
    if not ok:
        return HTMLResponse(_page(req, "Incorrect email or password."), status_code=401)

    claims["subject"] = email
    code = issue_code_after_login(claims)
    return RedirectResponse(redirect_after_login(claims, code), status_code=302)
