from dataclasses import dataclass
from typing import Dict, Tuple

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


def solve_ilp(map_data: MapData, max_walls: int) -> SolverResult:
    candidates = candidate_tiles(map_data)
    adjacency = build_adjacency(map_data)

    problem = pulp.LpProblem("horse_enclosure", pulp.LpMaximize)

    states = ("grass", "pasture", "wall")
    tile_vars: Dict[Coord, Dict[Assignment, pulp.LpVariable]] = {}

    for r, c in candidates:
        tile_vars[(r, c)] = {
            state: pulp.LpVariable(f"b_{state}_{r}_{c}", lowBound=0, upBound=1, cat="Binary")
            for state in states
        }
        # Each tile must pick exactly one state.
        problem += sum(tile_vars[(r, c)].values()) == 1

        # Boundary tiles cannot be walls (per work plan assumption).
        if r in (0, map_data.height - 1) or c in (0, map_data.width - 1):
            problem += tile_vars[(r, c)]["wall"] == 0

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

    solver = pulp.PULP_CBC_CMD(msg=False)
    problem.solve(solver)

    status = pulp.LpStatus.get(problem.status, "Unknown")
    assignments: Dict[Coord, Assignment] = {}
    for coord, vars_for_tile in tile_vars.items():
        chosen_state = max(vars_for_tile.items(), key=lambda item: item[1].value())[0]
        assignments[coord] = chosen_state

    objective_value = pulp.value(problem.objective) if problem.objective is not None else None
    return SolverResult(status=status, objective=objective_value, assignments=assignments)
