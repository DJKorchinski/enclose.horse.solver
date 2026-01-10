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

    states = ("grass", "pasture", "wall")
    tile_vars: Dict[Coord, Dict[Assignment, pulp.LpVariable]] = {}
    inside_vars: Dict[Coord, pulp.LpVariable] = {}

    boundary_candidates = _boundary_coords(map_data, candidates)

    for r, c in candidates:
        tile_vars[(r, c)] = {
            state: pulp.LpVariable(f"b_{state}_{r}_{c}", lowBound=0, upBound=1, cat="Binary")
            for state in states
        }
        inside_vars[(r, c)] = pulp.LpVariable(f"x_inside_{r}_{c}", lowBound=0, upBound=1, cat="Binary")

        # Each tile must pick exactly one state.
        problem += sum(tile_vars[(r, c)].values()) == 1

        # Pasture only if inside the enclosure (reachable from the horse).
        problem += tile_vars[(r, c)]["pasture"] <= inside_vars[(r, c)]

        # Cannot be inside if it's a wall.
        problem += inside_vars[(r, c)] <= 1 - tile_vars[(r, c)]["wall"]

        # Boundary tiles cannot be part of the inside region.
        if (r, c) in boundary_candidates:
            problem += inside_vars[(r, c)] == 0

    # Horse is always inside and not a wall.
    inside_vars[root] = pulp.LpVariable("x_inside_horse", lowBound=1, upBound=1, cat="Binary")

    # Tiles adjacent to the horse cannot be grass.
    hr, hc = map_data.horse
    for nr, nc in map_data.neighbors(hr, hc):
        if (nr, nc) in candidates:
            problem += tile_vars[(nr, nc)]["grass"] == 0

    # Objective: maximize 1 (horse) + pasture tiles.
    problem += 1 + pulp.lpSum(tile_vars[(r, c)]["pasture"] for r, c in candidates)

    # Wall budget.
    problem += pulp.lpSum(tile_vars[(r, c)]["wall"] for r, c in candidates) <= max_walls

    # Adjacency consistency: adjacent tiles are same type or at least one is a wall.
    handled_edges: set[Tuple[Coord, Coord]] = set()
    for r, c in adjacency:
        for nr, nc in adjacency[(r, c)]:
            edge = tuple(sorted(((r, c), (nr, nc))))
            if edge in handled_edges:
                continue
            handled_edges.add(edge)

            if (r, c) not in tile_vars or (nr, nc) not in tile_vars:
                continue  # Skip edges involving the horse for state matching.

            z = pulp.LpVariable(f"z_{r}_{c}__{nr}_{nc}", lowBound=0, upBound=1, cat="Binary")
            z_p = pulp.LpVariable(f"z_p_{r}_{c}__{nr}_{nc}", lowBound=0, upBound=1, cat="Binary")
            z_g = pulp.LpVariable(f"z_g_{r}_{c}__{nr}_{nc}", lowBound=0, upBound=1, cat="Binary")

            problem += z - z_p - z_g == 0

            problem += z_p <= tile_vars[(r, c)]["pasture"]
            problem += z_p <= tile_vars[(nr, nc)]["pasture"]
            problem += z_p >= tile_vars[(r, c)]["pasture"] + tile_vars[(nr, nc)]["pasture"] - 1

            problem += z_g <= tile_vars[(r, c)]["grass"]
            problem += z_g <= tile_vars[(nr, nc)]["grass"]
            problem += z_g >= tile_vars[(r, c)]["grass"] + tile_vars[(nr, nc)]["grass"] - 1

            problem += tile_vars[(r, c)]["wall"] + tile_vars[(nr, nc)]["wall"] + z >= 1

    # Connectivity / enclosure via single-commodity flow to keep inside region attached to horse and away from boundary.
    big_m = len(candidates) + 1
    flow_vars: Dict[Tuple[Coord, Coord], pulp.LpVariable] = {}
    for r, c in adjacency:
        for nr, nc in adjacency[(r, c)]:
            flow_vars[(r, c), (nr, nc)] = pulp.LpVariable(
                f"f_{r}_{c}__{nr}_{nc}", lowBound=0, upBound=big_m, cat="Continuous"
            )
            # Capacity respects inside status and walls on the source node (when applicable).
            problem += flow_vars[(r, c), (nr, nc)] <= big_m * inside_vars[(r, c)]
            if (r, c) in tile_vars:
                problem += flow_vars[(r, c), (nr, nc)] <= big_m * (1 - tile_vars[(r, c)]["wall"])

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
    for coord, vars_for_tile in tile_vars.items():
        chosen_state = max(vars_for_tile.items(), key=lambda item: item[1].value())[0]
        assignments[coord] = chosen_state

    objective_value = pulp.value(problem.objective) if problem.objective is not None else None
    return SolverResult(status=status, objective=objective_value, assignments=assignments)
