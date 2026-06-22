"""MCP server entrypoint: ``python -m app.mcp.server``.

Registers the schedule tools (SCOPE §5.3) on a FastMCP server over stdio. Every
tool routes through the shared service layer, so chat writes are validated,
recalculated, and audited identically to web writes.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.mcp import tools

# host/port matter only for HTTP transport (a remote connector on Render); for
# stdio they're ignored. Render injects PORT; default 8001 locally.
mcp = FastMCP(
    "rise-schedule-hub",
    host="0.0.0.0",
    port=int(os.environ.get("PORT", "8001")),
)


@mcp.tool()
def list_projects() -> dict[str, Any]:
    """List all projects with stage and rolled-up start/finish dates."""
    return tools.list_projects()


@mcp.tool()
def get_schedule(project_id: int) -> dict[str, Any]:
    """Get the full schedule (tasks + dependencies + computed dates/float/critical)
    for a project."""
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
    project schedule recalculates and is validated before saving."""
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
def generate_report(scope: str, report_type: str) -> dict[str, Any]:
    """Generate a report. ``scope`` = 'all' or a project id; ``report_type`` =
    leadership_digest | slippage | what_changed."""
    return tools.generate_report(scope, report_type)


def main() -> None:
    # Default to stdio (local Claude Desktop / Claude Code, launched as a
    # subprocess). Use --http (or MCP_TRANSPORT=http) to serve Streamable HTTP at
    # /mcp for a hosted remote connector (Render).
    use_http = "--http" in sys.argv or os.environ.get("MCP_TRANSPORT") == "http"
    mcp.run(transport="streamable-http" if use_http else "stdio")


if __name__ == "__main__":
    main()
