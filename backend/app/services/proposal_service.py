"""Pending "what-if" proposals — the dry-run layer.

A proposal is a list of mutations (the same ops the scheduling service applies)
stored on ``projects.pending_proposal`` without touching the live schedule. The
proposed schedule is **computed on read**: apply the mutations to in-memory
copies of the project's tasks/deps and run the pure CPM engine. Applying replays
the mutations through the real scheduling service; discarding just clears them.

This lets chat (MCP) and the web app share one in-flight proposal: chat proposes,
the user reviews the diff in either surface, and approval applies it for real.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.engine import compute_schedule
from app.engine.types import (
    DependencyType,
    ScheduleDependency,
    ScheduleResult,
    ScheduleTask,
)
from app.models import Dependency, Task
from app.repositories import project_repo
from app.schemas.dependency import DependencyOut
from app.schemas.project import (
    ChangeSide,
    ProjectOut,
    ProposalOut,
    ProposalStep,
    ScheduleOut,
    TaskChange,
)
from app.schemas.task import TaskOut
from app.services import project_service, scheduling_service
from app.services.scheduling_service import WRITABLE_TASK_FIELDS

# Defaults for a task created inside a proposal (mirrors TaskCreate defaults).
_CREATE_DEFAULTS = {
    "name": "New task",
    "wbs": None,
    "trade": None,
    "building": None,
    "duration_days": 0,
    "percent_complete": 0.0,
    "status": "not_started",
    "is_milestone": False,
    "actual_start": None,
    "actual_finish": None,
    "start_no_earlier_than": None,
    "version": 1,
    "updated_by": None,
    "updated_at": None,
    "external_ref": None,
    "procore_id": None,
}


# ---- in-memory snapshots -----------------------------------------------------

def _snapshot(t: Task) -> dict[str, Any]:
    """A plain, detached copy of a task's editable + identity fields."""
    return {
        "id": t.id,
        "project_id": t.project_id,
        "name": t.name,
        "wbs": t.wbs,
        "trade": t.trade,
        "building": t.building,
        "duration_days": t.duration_days,
        "percent_complete": t.percent_complete,
        "status": t.status.value if hasattr(t.status, "value") else t.status,
        "is_milestone": t.is_milestone,
        "actual_start": t.actual_start,
        "actual_finish": t.actual_finish,
        "start_no_earlier_than": t.start_no_earlier_than,
        "version": t.version,
        "updated_by": t.updated_by,
        "updated_at": t.updated_at,
        "external_ref": t.external_ref,
        "procore_id": t.procore_id,
    }


def _dep_snapshot(d: Dependency) -> dict[str, Any]:
    return {
        "id": d.id,
        "predecessor_id": d.predecessor_id,
        "successor_id": d.successor_id,
        "type": d.type.value if hasattr(d.type, "value") else d.type,
        "lag_days": d.lag_days,
    }


def _engine_task(w: dict[str, Any]) -> ScheduleTask:
    return ScheduleTask(
        id=w["id"],
        duration_days=0 if w["is_milestone"] else int(w["duration_days"] or 0),
        is_milestone=bool(w["is_milestone"]),
        actual_start=w["actual_start"],
        actual_finish=w["actual_finish"],
        wbs=w["wbs"],
    )


def _engine_dep(d: dict[str, Any]) -> ScheduleDependency:
    return ScheduleDependency(
        predecessor_id=d["predecessor_id"],
        successor_id=d["successor_id"],
        type=DependencyType(d["type"]),
        lag_days=int(d["lag_days"] or 0),
    )


# ---- mutation field accessors (tolerate a few key spellings) -----------------

def _dep_type(m: dict[str, Any]) -> str:
    return m.get("type") or m.get("dep_type") or "FS"


def _dep_lag(m: dict[str, Any]) -> int:
    return int(m.get("lag", m.get("lag_days", 0)) or 0)


def _dep_endpoints(m: dict[str, Any]) -> tuple[Any, Any]:
    pred = m.get("predecessor", m.get("pred"))
    succ = m.get("successor", m.get("succ"))
    return pred, succ


# ---- preview (compute the proposed schedule + diff without persisting) -------

def _preview(
    session: Session, project_id: int, mutations: list[dict[str, Any]]
) -> tuple[ScheduleOut, list[TaskChange]]:
    """Apply ``mutations`` to in-memory copies and recompute. Raises
    CircularDependencyError / DateConflictError on an invalid proposal (so it's
    reported, never stored). DB is never written."""
    sched = project_service.get_schedule(session, project_id)
    if sched is None:
        raise ValueError(f"Unknown project {project_id}")
    project, tasks, deps = sched

    # Live (persisted) side of the diff.
    current: dict[int, ChangeSide] = {
        t.id: ChangeSide(
            planned_start=t.planned_start,
            planned_finish=t.planned_finish,
            duration_days=t.duration_days,
        )
        for t in tasks
    }
    orig_by_id = {t.id: _snapshot(t) for t in tasks}
    names = {t.id: t.name for t in tasks}

    working: list[dict[str, Any]] = [_snapshot(t) for t in tasks]
    by_id = {w["id"]: w for w in working}
    working_deps: list[dict[str, Any]] = [_dep_snapshot(d) for d in deps]

    ref_map: dict[str, int] = {}
    next_temp_task = [-1]
    next_temp_dep = [-1]

    def resolve(endpoint: Any) -> int:
        if isinstance(endpoint, str):
            if endpoint in ref_map:
                return ref_map[endpoint]
            try:
                return int(endpoint)
            except ValueError as exc:
                raise ValueError(f"Unknown task ref '{endpoint}'") from exc
        return endpoint

    for m in mutations:
        op = m.get("op")
        if op == "update_task":
            tid = m["task_id"]
            w = by_id.get(tid)
            if w is None:
                raise ValueError(f"Unknown task {tid}")
            for k, v in (m.get("fields") or {}).items():
                if k in WRITABLE_TASK_FIELDS:
                    w[k] = v
        elif op == "create_task":
            tid = next_temp_task[0]
            next_temp_task[0] -= 1
            fields = m.get("fields") or {}
            w = {"id": tid, "project_id": project_id, **_CREATE_DEFAULTS}
            for k, v in fields.items():
                if k in _CREATE_DEFAULTS:
                    w[k] = v
            working.append(w)
            by_id[tid] = w
            ref = m.get("ref")
            if ref is not None:
                ref_map[str(ref)] = tid
        elif op == "delete_task":
            tid = m["task_id"]
            w = by_id.pop(tid, None)
            if w is not None:
                working.remove(w)
                working_deps[:] = [
                    d for d in working_deps
                    if d["predecessor_id"] != tid and d["successor_id"] != tid
                ]
        elif op == "create_dependency":
            pred, succ = _dep_endpoints(m)
            did = next_temp_dep[0]
            next_temp_dep[0] -= 1
            working_deps.append({
                "id": did,
                "predecessor_id": resolve(pred),
                "successor_id": resolve(succ),
                "type": DependencyType(_dep_type(m)).value,
                "lag_days": _dep_lag(m),
            })
        elif op == "delete_dependency":
            did = m.get("dependency_id")
            if did is not None:
                working_deps[:] = [d for d in working_deps if d["id"] != did]
            else:
                pred, succ = _dep_endpoints(m)
                pred, succ = resolve(pred), resolve(succ)
                working_deps[:] = [
                    d for d in working_deps
                    if not (d["predecessor_id"] == pred and d["successor_id"] == succ)
                ]
        else:
            raise ValueError(f"Unknown mutation op '{op}'")

    result = compute_schedule(
        [_engine_task(w) for w in working],
        [_engine_dep(d) for d in working_deps],
        project.anchor_date,
    )

    schedule = _proposed_schedule(project, working, working_deps, result)
    changes = _diff(working, result, current, orig_by_id, names)
    return schedule, changes


def _proposed_schedule(
    project,
    working: list[dict[str, Any]],
    working_deps: list[dict[str, Any]],
    result: ScheduleResult,
) -> ScheduleOut:
    task_outs: list[TaskOut] = []
    for w in working:
        r = result.tasks.get(w["id"])
        out = dict(w)
        out["planned_start"] = r.early_start_date if r else None
        out["planned_finish"] = r.early_finish_date if r else None
        out["late_start"] = r.late_start_date if r else None
        out["late_finish"] = r.late_finish_date if r else None
        out["total_float"] = r.total_float if r else None
        out["free_float"] = r.free_float if r else None
        out["is_critical"] = bool(r.is_critical) if r else False
        task_outs.append(TaskOut.model_validate(out))

    dep_outs = [
        DependencyOut.model_validate({
            "id": d["id"],
            "predecessor_id": d["predecessor_id"],
            "successor_id": d["successor_id"],
            "type": d["type"],
            "lag_days": d["lag_days"],
            "is_critical": (d["predecessor_id"], d["successor_id"])
            in result.critical_dependencies,
        })
        for d in working_deps
    ]

    proj_out = ProjectOut.model_validate(project).model_copy(update={
        "planned_start": result.project_start,
        "planned_finish": result.project_finish,
    })
    return ScheduleOut(project=proj_out, tasks=task_outs, dependencies=dep_outs)


def _diff(
    working: list[dict[str, Any]],
    result: ScheduleResult,
    current: dict[int, ChangeSide],
    orig_by_id: dict[int, dict[str, Any]],
    names: dict[int, str],
) -> list[TaskChange]:
    changes: list[TaskChange] = []
    proposed_ids = {w["id"] for w in working}

    for w in working:
        r = result.tasks.get(w["id"])
        ps = r.early_start_date if r else None
        pf = r.early_finish_date if r else None
        proposed = ChangeSide(
            planned_start=ps, planned_finish=pf, duration_days=w["duration_days"]
        )
        if w["id"] < 0:  # created in this proposal
            changes.append(TaskChange(
                task_id=w["id"], name=w["name"], change_type="new",
                current=None, proposed=proposed,
            ))
            continue
        cur = current.get(w["id"])
        if cur is None:
            continue
        moved = cur.planned_start != ps or cur.planned_finish != pf
        modified = any(
            orig_by_id[w["id"]].get(k) != w.get(k) for k in WRITABLE_TASK_FIELDS
        )
        if moved:
            changes.append(TaskChange(
                task_id=w["id"], name=w["name"], change_type="moved",
                current=cur, proposed=proposed,
            ))
        elif modified:
            changes.append(TaskChange(
                task_id=w["id"], name=w["name"], change_type="modified",
                current=cur, proposed=proposed,
            ))

    for tid, cur in current.items():
        if tid not in proposed_ids:
            changes.append(TaskChange(
                task_id=tid, name=names.get(tid, ""), change_type="removed",
                current=cur, proposed=None,
            ))
    return changes


# ---- proposal steps (accumulate; one proposal = an ordered list of steps) -----
#
# A proposal stores its mutations as a list of *steps* — each step is one
# `propose_changes` call: ``{summary, mutations, created_at}``. Stacking appends a
# step; undo-last pops the last one. The proposed schedule is computed from the
# flattened mutations (every step's mutations concatenated in order), so the
# preview/diff are always cumulative. Apply replays the flattened list for real.

def _steps(meta: dict[str, Any]) -> list[dict[str, Any]]:
    """The proposal's steps, tolerating the legacy flat ``{mutations}`` shape."""
    if meta.get("steps") is not None:
        return list(meta["steps"])
    if meta.get("mutations"):
        return [{
            "summary": meta.get("summary"),
            "mutations": meta["mutations"],
            "created_at": meta.get("created_at"),
        }]
    return []


def _flatten(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for step in steps:
        out.extend(step.get("mutations") or [])
    return out


def _store_steps(
    session: Session,
    project_id: int,
    steps: list[dict[str, Any]],
    actor: str,
    created_at: str | None,
) -> None:
    """Persist the step list (or clear the proposal when empty)."""
    project = project_repo.get(session, project_id)
    if project is None:
        raise ValueError(f"Unknown project {project_id}")
    if not steps:
        project.pending_proposal = None
    else:
        project.pending_proposal = {
            "actor": actor,
            "created_at": created_at or datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "steps": steps,
        }
    session.commit()


def _proposal_steps(meta: dict[str, Any]) -> list[ProposalStep]:
    return [
        ProposalStep(
            summary=s.get("summary"),
            change_count=len(s.get("mutations") or []),
            created_at=s.get("created_at"),
        )
        for s in _steps(meta)
    ]


# ---- public API --------------------------------------------------------------

def add_step(
    session: Session,
    project_id: int,
    mutations: list[dict[str, Any]],
    summary: str | None = None,
    actor: str = "chat",
) -> ProposalOut:
    """Append a step to the pending proposal (creating one if none exists),
    keeping the user's earlier staged changes. The COMBINED proposal is validated
    via a dry-run — a step that would create a cycle/date conflict on top of
    what's staged is rejected and NOT added; the prior steps stay intact."""
    project = project_repo.get(session, project_id)
    if project is None:
        raise ValueError(f"Unknown project {project_id}")
    existing = _steps(project.pending_proposal) if project.pending_proposal else []
    created_at = (project.pending_proposal or {}).get("created_at")
    new_step = {
        "summary": summary,
        "mutations": mutations,
        "created_at": datetime.now(UTC).isoformat(),
    }
    candidate = [*existing, new_step]
    _preview(session, project_id, _flatten(candidate))  # validate combined; raises
    _store_steps(session, project_id, candidate, actor, created_at)
    proposal = get_pending(session, project_id)
    assert proposal is not None  # we just stored it
    return proposal


def set_pending(
    session: Session,
    project_id: int,
    mutations: list[dict[str, Any]],
    summary: str | None = None,
    actor: str = "chat",
    replace: bool = True,
) -> ProposalOut:
    """Stage a proposal. ``replace=True`` (default) discards any staged steps and
    starts over with this one step; ``replace=False`` appends (same as
    ``add_step``). Raises on an invalid proposal — nothing is stored."""
    if not replace:
        return add_step(session, project_id, mutations, summary, actor)
    _preview(session, project_id, mutations)  # validate; raises on cycle/conflict
    step = {
        "summary": summary,
        "mutations": mutations,
        "created_at": datetime.now(UTC).isoformat(),
    }
    _store_steps(session, project_id, [step], actor, created_at=None)
    proposal = get_pending(session, project_id)
    assert proposal is not None  # we just set it
    return proposal


def undo_last(session: Session, project_id: int, actor: str = "chat") -> ProposalOut | None:
    """Drop the most recently added step. If no steps remain, the proposal is
    cleared. Returns the updated proposal, or None when nothing is left."""
    project = project_repo.get(session, project_id)
    if project is None or not project.pending_proposal:
        return None
    steps = _steps(project.pending_proposal)
    created_at = project.pending_proposal.get("created_at")
    steps = steps[:-1]
    _store_steps(session, project_id, steps, actor, created_at)
    return get_pending(session, project_id)


def get_pending(session: Session, project_id: int) -> ProposalOut | None:
    """The pending proposal with its freshly-computed schedule + diff, or None."""
    project = project_repo.get(session, project_id)
    if project is None or not project.pending_proposal:
        return None
    meta = project.pending_proposal
    steps = _steps(meta)
    schedule, changes = _preview(session, project_id, _flatten(steps))
    # The headline summary is the most recent step's (the rest show in `steps`).
    latest_summary = next(
        (s.get("summary") for s in reversed(steps) if s.get("summary")), None
    )
    return ProposalOut(
        summary=latest_summary,
        actor=meta.get("actor"),
        created_at=meta.get("created_at"),
        schedule=schedule,
        changes=changes,
        steps=_proposal_steps(meta),
    )


def apply_pending(
    session: Session, project_id: int, actor: str = "chat"
) -> ScheduleOut | None:
    """Replay the pending mutations through the real scheduling service, then
    clear the proposal. Returns the new live schedule, or None if none pending."""
    project = project_repo.get(session, project_id)
    if project is None or not project.pending_proposal:
        return None
    mutations = _flatten(_steps(project.pending_proposal))
    ref_map: dict[str, int] = {}

    def resolve(endpoint: Any) -> int:
        if isinstance(endpoint, str):
            if endpoint in ref_map:
                return ref_map[endpoint]
            return int(endpoint)
        return endpoint

    for m in mutations:
        op = m.get("op")
        if op == "update_task":
            scheduling_service.update_task(
                session, m["task_id"], m.get("fields") or {}, actor=actor
            )
        elif op == "create_task":
            task, _ = scheduling_service.create_task(
                session, project_id, m.get("fields") or {}, actor=actor
            )
            ref = m.get("ref")
            if ref is not None:
                ref_map[str(ref)] = task.id
        elif op == "delete_task":
            scheduling_service.delete_task(session, m["task_id"], actor=actor)
        elif op == "create_dependency":
            pred, succ = _dep_endpoints(m)
            scheduling_service.create_dependency(
                session, resolve(pred), resolve(succ),
                DependencyType(_dep_type(m)).value, _dep_lag(m), actor=actor,
            )
        elif op == "delete_dependency":
            did = m.get("dependency_id")
            if did is not None:
                scheduling_service.delete_dependency(session, did, actor=actor)
        else:
            raise ValueError(f"Unknown mutation op '{op}'")

    project = project_repo.get(session, project_id)
    project.pending_proposal = None
    session.commit()
    return _current_schedule(session, project_id)


def discard_pending(session: Session, project_id: int) -> bool:
    """Clear the pending proposal. Returns True if one was cleared."""
    project = project_repo.get(session, project_id)
    if project is None or not project.pending_proposal:
        return False
    project.pending_proposal = None
    session.commit()
    return True


def _current_schedule(session: Session, project_id: int) -> ScheduleOut | None:
    sched = project_service.get_schedule(session, project_id)
    if sched is None:
        return None
    project, tasks, deps = sched
    return ScheduleOut(
        project=ProjectOut.model_validate(project),
        tasks=[TaskOut.model_validate(t) for t in tasks],
        dependencies=[DependencyOut.model_validate(d) for d in deps],
    )


__all__ = [
    "add_step", "set_pending", "get_pending", "undo_last",
    "apply_pending", "discard_pending", "date",
]
