"""Dependency-graph construction, topological sort, and cycle extraction.

Hand-rolled (not networkx): the CPM relaxation is custom per dependency type in
working-day index space, so a general graph library would only get in the way.
Kahn's algorithm doubles as the cycle detector.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engine.errors import CircularDependencyError
from app.engine.types import ScheduleDependency, ScheduleTask


@dataclass
class Graph:
    """Adjacency structures over a set of tasks and their dependency edges."""

    nodes: dict[int, ScheduleTask]
    # successors[id] = edges where id is the predecessor
    successors: dict[int, list[ScheduleDependency]]
    # predecessors[id] = edges where id is the successor
    predecessors: dict[int, list[ScheduleDependency]]
    indegree: dict[int, int] = field(default_factory=dict)


def build_graph(
    tasks: list[ScheduleTask], dependencies: list[ScheduleDependency]
) -> Graph:
    """Build the in/out adjacency graph, validating that edges reference tasks."""
    nodes = {t.id: t for t in tasks}
    successors: dict[int, list[ScheduleDependency]] = {tid: [] for tid in nodes}
    predecessors: dict[int, list[ScheduleDependency]] = {tid: [] for tid in nodes}
    indegree: dict[int, int] = {tid: 0 for tid in nodes}

    for dep in dependencies:
        if dep.predecessor_id not in nodes:
            raise ValueError(f"Dependency references unknown predecessor {dep.predecessor_id}")
        if dep.successor_id not in nodes:
            raise ValueError(f"Dependency references unknown successor {dep.successor_id}")
        successors[dep.predecessor_id].append(dep)
        predecessors[dep.successor_id].append(dep)
        indegree[dep.successor_id] += 1

    return Graph(nodes=nodes, successors=successors, predecessors=predecessors, indegree=indegree)


def topological_order(graph: Graph) -> list[int]:
    """Return task ids in dependency order using Kahn's algorithm.

    Raises :class:`CircularDependencyError` (with the offending cycle path) if
    the graph contains a cycle.
    """
    indegree = dict(graph.indegree)
    queue = [tid for tid, deg in indegree.items() if deg == 0]
    order: list[int] = []

    while queue:
        node = queue.pop()
        order.append(node)
        for dep in graph.successors[node]:
            indegree[dep.successor_id] -= 1
            if indegree[dep.successor_id] == 0:
                queue.append(dep.successor_id)

    if len(order) != len(graph.nodes):
        residual = [tid for tid, deg in indegree.items() if deg > 0]
        raise CircularDependencyError(_extract_cycle(graph, residual))

    return order


def _extract_cycle(graph: Graph, residual: list[int]) -> list[int]:
    """DFS over the nodes still carrying in-degree to recover an actual cycle
    path, e.g. ``[A, B, C, A]``, for a useful error message."""
    residual_set = set(residual)
    visited: set[int] = set()
    stack: list[int] = []
    on_stack: set[int] = set()

    def dfs(node: int) -> list[int] | None:
        visited.add(node)
        stack.append(node)
        on_stack.add(node)
        for dep in graph.successors[node]:
            nxt = dep.successor_id
            if nxt not in residual_set:
                continue
            if nxt in on_stack:
                # Found the cycle: slice the stack from the first occurrence.
                idx = stack.index(nxt)
                return stack[idx:] + [nxt]
            if nxt not in visited:
                found = dfs(nxt)
                if found is not None:
                    return found
        stack.pop()
        on_stack.discard(node)
        return None

    for start in residual:
        if start not in visited:
            cycle = dfs(start)
            if cycle is not None:
                return cycle
    # Fallback: should not happen if residual is non-empty, but be safe.
    return residual + [residual[0]] if residual else []
