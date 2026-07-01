"""MCP server entrypoint: ``python -m app.mcp.server``.

Registers the schedule tools (SCOPE §5.3) on a FastMCP server over stdio. Every
tool routes through the shared service layer, so chat writes are validated,
recalculated, and audited identically to web writes.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from mcp.server.auth.settings import (
    AuthSettings,
    ClientRegistrationOptions,
    RevocationOptions,
)
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.config import get_settings
from app.mcp import tools
from app.mcp.oauth import SchedulingHubOAuthProvider
from app.mcp.oauth_login import oauth_login

# Decide the transport at import time so HTTP can be constructed with OAuth.
# Default to stdio (local Claude Desktop / Claude Code subprocess); --http (or
# MCP_TRANSPORT=http) serves Streamable HTTP at /mcp for the hosted Render connector.
_USE_HTTP = "--http" in sys.argv or os.environ.get("MCP_TRANSPORT") == "http"

# Over HTTP the server is a self-hosted OAuth 2.1 authorization server: the Claude.ai
# connector runs the OAuth flow, the user signs in with their scheduling-hub account,
# and the issued access token is a per-user scope:"mcp" JWT (see app/mcp/oauth.py). So
# chat changes are attributed to the real user and scoped to their projects. Stdio is a
# trusted local subprocess and stays unauthenticated.
_auth_kwargs: dict[str, Any] = {}
if _USE_HTTP:
    _settings = get_settings()
    _auth_kwargs = {
        "auth_server_provider": SchedulingHubOAuthProvider(),
        "auth": AuthSettings(
            issuer_url=_settings.mcp_issuer_url,
            resource_server_url=_settings.mcp_public_url,
            required_scopes=["mcp"],
            client_registration_options=ClientRegistrationOptions(
                enabled=True, valid_scopes=["mcp"], default_scopes=["mcp"]
            ),
            revocation_options=RevocationOptions(enabled=True),
        ),
    }

# host/port matter only for HTTP transport (a remote connector on Render); for
# stdio they're ignored. Render injects PORT; default 8001 locally.
mcp = FastMCP(
    "rise-schedule-hub",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", "8001")),
    **_auth_kwargs,
)

# The OAuth sign-in page (the authorize step redirects the user here). Harmless on
# stdio (only the HTTP app serves routes).
mcp.custom_route("/oauth/login", methods=["GET", "POST"])(oauth_login)


async def health(_request: Request) -> JSONResponse:
    """Cheap liveness probe (no DB) so Render can health-check the MCP dyno and the
    web app can wake it before the user connects — /mcp itself refuses a plain GET."""
    return JSONResponse({"status": "ok"})


mcp.custom_route("/health", methods=["GET"])(health)


@mcp.tool()
def list_projects() -> dict[str, Any]:
    """List all projects with stage and rolled-up start/finish dates."""
    return tools.list_projects()


@mcp.tool()
def get_schedule(project_id: int) -> dict[str, Any]:
    """Get the full schedule (tasks + dependencies + computed dates/float/critical)
    for a project. Each task carries a ``group`` (its phase/building names, e.g.
    "Phase 2 / Building 13") and the project carries a ``wbs_labels`` map (WBS
    prefix -> name). When referring to a phase or building, use these names, NOT the
    raw WBS code (say "Building 13", not "2.2")."""
    return tools.get_schedule(project_id)


@mcp.tool()
def create_task(project_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    """Create a task. ``fields`` may include name, wbs, duration_days,
    percent_complete, status, is_milestone, actual_start, actual_finish.
    The schedule recalculates automatically."""
    return tools.create_task(project_id, fields)


@mcp.tool()
def update_task(task_id: int, fields: dict[str, Any]) -> dict[str, Any]:
    """Update task fields (progress %, dates, status, duration, ...). The whole
    project schedule recalculates and is validated before saving.

    Rescheduling a START date:
    - To move a task that has NOT started yet (a plan change — "the trade can start
      6/30", a delay, a lookahead update), set ``start_no_earlier_than``. It's a
      planning constraint: a floor on the computed start that still respects
      predecessors, and it does NOT log work as having happened.
    - Reserve ``actual_start`` for recording that work has ACTUALLY begun. Do not
      set a future ``actual_start`` to reschedule — that logs a fake actual."""
    return tools.update_task(task_id, fields)


@mcp.tool()
def delete_task(task_id: int) -> dict[str, Any]:
    """Delete a task and recalculate the schedule."""
    return tools.delete_task(task_id)


@mcp.tool()
def create_dependency(
    predecessor_id: int, successor_id: int, dep_type: str = "FS", lag_days: int = 0
) -> dict[str, Any]:
    """Link two tasks. ``dep_type`` is FS|SS|FF|SF; ``lag_days`` may be negative.
    A link that would create a cycle is rejected and nothing is saved."""
    return tools.create_dependency(predecessor_id, successor_id, dep_type, lag_days)


@mcp.tool()
def get_critical_path(project_id: int) -> dict[str, Any]:
    """Return the project's critical-path tasks in order."""
    return tools.get_critical_path(project_id)


@mcp.tool()
def propose_changes(
    project_id: int,
    mutations: list[dict[str, Any]],
    summary: str | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    """Stage a what-if proposal WITHOUT applying it, and return the cumulative diff
    to show the user (downstream date shifts, new project finish). Use this for any
    requested schedule change so the user can review before it's committed.

    This ADDS to any pending proposal — the user keeps stacking changes across
    messages, then approves once. The returned diff and ``steps`` list reflect ALL
    staged changes so far. Pass ``replace=True`` to discard what's staged and start
    over. Use ``undo_last_change`` to drop the most recent step.

    ``mutations`` is an ordered list; each item is ``{"op": ..., ...}``:
      - ``{"op": "update_task", "task_id": 12, "fields": {"duration_days": 8}}``
        (to reschedule a not-yet-started task's start, set
        ``{"start_no_earlier_than": "2026-06-30"}`` — a planning constraint — NOT a
        future ``actual_start``)
      - ``{"op": "create_task", "ref": "t1", "fields": {"name": "...", "wbs": "1.1.5",
        "duration_days": 5}}`` (``ref`` lets a later dependency point at it)
      - ``{"op": "delete_task", "task_id": 12}``
      - ``{"op": "create_dependency", "predecessor": 12, "successor": "t1",
        "type": "FS", "lag": 0}`` (endpoints may be a task id or a create ref)
      - ``{"op": "delete_dependency", "dependency_id": 7}``
    A proposal that would create a cycle or date conflict (on top of what's already
    staged) is rejected and not added; prior steps stay intact. After the user
    approves, call ``apply_proposal``."""
    return tools.propose_changes(project_id, mutations, summary, replace)


@mcp.tool()
def undo_last_change(project_id: int) -> dict[str, Any]:
    """Remove the most recently staged step from the pending what-if proposal,
    keeping earlier staged changes. Clears the proposal if it was the last step."""
    return tools.undo_last_change(project_id)


@mcp.tool()
def get_proposal(project_id: int) -> dict[str, Any]:
    """Return the project's pending what-if proposal diff (or ``pending: False``)."""
    return tools.get_proposal(project_id)


@mcp.tool()
def apply_proposal(project_id: int) -> dict[str, Any]:
    """Apply the project's pending proposal for real (recalculates + audits) and
    clear it. Call only after the user approves the proposed changes."""
    return tools.apply_proposal(project_id)


@mcp.tool()
def discard_proposal(project_id: int) -> dict[str, Any]:
    """Discard the project's pending proposal without applying it."""
    return tools.discard_proposal(project_id)


@mcp.tool()
def generate_report(scope: str, report_type: str) -> dict[str, Any]:
    """Generate a report. ``scope`` = 'all' or a project id; ``report_type`` =
    leadership_digest | slippage | what_changed."""
    return tools.generate_report(scope, report_type)


def main() -> None:
    mcp.run(transport="streamable-http" if _USE_HTTP else "stdio")


if __name__ == "__main__":
    main()
