from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

import pulp

from .graph import build_adjacency, candidate_tiles
from .parser import Coord, MapData


Assignment = str  # "grass" | "pasture" | "wall"


@dataclass
class SolverResult:
    status: str
    objective: float | None
    assignments: Dict[Coord, Assignment]

    def walls_used(self) -> int:
        return sum(1 for state in self.assignments.values() if state == "wall")

    def pasture_tiles(self) -> int:
        return sum(1 for state in self.assignments.values() if state == "pasture")


def _boundary_coords(map_data: MapData, coords: Iterable[Coord]) -> set[Coord]:
    return {
        (r, c)
        for r, c in coords
        if r in (0, map_data.height - 1) or c in (0, map_data.width - 1)
    }


def solve_ilp(map_data: MapData, max_walls: int) -> SolverResult:
    candidates = candidate_tiles(map_data)
    adjacency = build_adjacency(map_data)

    root = map_data.horse
    nodes = set(candidates)
    nodes.add(root)

    # Add horse adjacency to candidates.
    adjacency[root] = []
    for nr, nc in map_data.neighbors(*root):
        if (nr, nc) in candidates:
            adjacency[root].append((nr, nc))
            adjacency.setdefault((nr, nc), []).append(root)

    problem = pulp.LpProblem("horse_enclosure", pulp.LpMaximize)

    wall_vars: Dict[Coord, pulp.LpVariable] = {}
    inside_vars: Dict[Coord, pulp.LpVariable] = {}

    boundary_candidates = _boundary_coords(map_data, candidates)

    for r, c in candidates:
        wall_vars[(r, c)] = pulp.LpVariable(f"b_wall_{r}_{c}", lowBound=0, upBound=1, cat="Binary")
        inside_vars[(r, c)] = pulp.LpVariable(f"x_inside_{r}_{c}", lowBound=0, upBound=1, cat="Binary")

        # Inside region and wall are mutually exclusive.
        problem += wall_vars[(r, c)] + inside_vars[(r, c)] <= 1

        # Portals cannot be walls.
        if (r, c) in map_data.portal_ids:
            problem += wall_vars[(r, c)] == 0

        # Cherries cannot be walls.
        if (r, c) in map_data.cherries:
            problem += wall_vars[(r, c)] == 0

        # Boundary tiles cannot be part of the inside region.
        if (r, c) in boundary_candidates:
            problem += inside_vars[(r, c)] == 0

    # Horse is always inside and not a wall.
    inside_vars[root] = pulp.LpVariable("x_inside_horse", lowBound=1, upBound=1, cat="Binary")
    wall_vars[root] = pulp.LpVariable("b_wall_horse", lowBound=0, upBound=0, cat="Binary")

    # Tiles adjacent to the horse cannot be walls (so flow can emanate).
    hr, hc = map_data.horse
    for nr, nc in map_data.neighbors(hr, hc):
        if (nr, nc) in candidates:
            problem += wall_vars[(nr, nc)] == 0

    # Objective: maximize 1 (horse) + inside tiles + cherry bonuses.
    cherry_bonus = pulp.lpSum(3 * inside_vars[(r, c)] for r, c in map_data.cherries if (r, c) in inside_vars)
    problem += 1 + pulp.lpSum(inside_vars[(r, c)] for r, c in candidates) + cherry_bonus

    # Wall budget.
    problem += pulp.lpSum(wall_vars[(r, c)] for r, c in candidates) <= max_walls

    # Separation constraints: if inside differs across an edge, at least one wall must be present.
    handled_edges: set[Tuple[Coord, Coord]] = set()
    for r, c in adjacency:
        for nr, nc in adjacency[(r, c)]:
            edge = tuple(sorted(((r, c), (nr, nc))))
            if edge in handled_edges:
                continue
            handled_edges.add(edge)
            ir = inside_vars.get((r, c), 0)
            inr = inside_vars.get((nr, nc), 0)
            wr = wall_vars.get((r, c), 0)
            wnr = wall_vars.get((nr, nc), 0)
            problem += ir - inr <= wr + wnr
            problem += inr - ir <= wr + wnr

    # Connectivity / enclosure via single-commodity flow to keep inside region attached to horse and away from boundary.
    big_m = len(candidates) + 1
    flow_vars: Dict[Tuple[Coord, Coord], pulp.LpVariable] = {}
    for r, c in adjacency:
        for nr, nc in adjacency[(r, c)]:
            flow_vars[(r, c), (nr, nc)] = pulp.LpVariable(
                f"f_{r}_{c}__{nr}_{nc}", lowBound=0, upBound=big_m, cat="Continuous"
            )
            # Capacity respects inside status and walls on the source node (when applicable).
            problem += flow_vars[(r, c), (nr, nc)] <= big_m * inside_vars.get((r, c), 0)
            problem += flow_vars[(r, c), (nr, nc)] <= big_m * (1 - wall_vars.get((r, c), 0))

    total_inside = pulp.lpSum(inside_vars[(r, c)] for r, c in candidates)

    for node in nodes:
        incoming = pulp.lpSum(flow_vars[(u, v)] for (u, v) in flow_vars if v == node)
        outgoing = pulp.lpSum(flow_vars[(u, v)] for (u, v) in flow_vars if u == node)
        if node == root:
            # Source pushes flow equal to number of inside tiles (excluding the horse).
            problem += outgoing - incoming == total_inside
        else:
            problem += incoming - outgoing == inside_vars[node]

    solver = pulp.PULP_CBC_CMD(msg=False)
    problem.solve(solver)

    status = pulp.LpStatus.get(problem.status, "Unknown")
    assignments: Dict[Coord, Assignment] = {}
    for coord in candidates:
        if wall_vars[coord].value() >= 0.5:
            assignments[coord] = "wall"
        elif inside_vars[coord].value() >= 0.5:
            assignments[coord] = "pasture"
        else:
            assignments[coord] = "grass"

    objective_value = pulp.value(problem.objective) if problem.objective is not None else None
    return SolverResult(status=status, objective=objective_value, assignments=assignments)
