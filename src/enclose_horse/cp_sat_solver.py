from typing import Dict, Tuple

from ortools.sat.python import cp_model

from .graph import build_adjacency, candidate_tiles
from .ilp_solver import Assignment, SolverResult
from .parser import Coord, MapData


def solve_cp_sat(map_data: MapData, max_walls: int) -> SolverResult:
    candidates = candidate_tiles(map_data)
    adjacency = build_adjacency(map_data)
    root = map_data.horse

    model = cp_model.CpModel()
    wall_vars: Dict[Coord, cp_model.IntVar] = {}
    inside_vars: Dict[Coord, cp_model.IntVar] = {}

    for coord in candidates:
        wall_vars[coord] = model.NewBoolVar(f"wall_{coord[0]}_{coord[1]}")
        inside_vars[coord] = model.NewBoolVar(f"inside_{coord[0]}_{coord[1]}")
        # Inside and wall are mutually exclusive.
        model.Add(wall_vars[coord] + inside_vars[coord] <= 1)

        if coord in map_data.portal_ids or coord in map_data.cherries or coord == root:
            model.Add(wall_vars[coord] == 0)

        if coord != root:
            r, c = coord
            if r in (0, map_data.height - 1) or c in (0, map_data.width - 1):
                model.Add(inside_vars[coord] == 0)

    # Horse fixed to inside.
    model.Add(inside_vars[root] == 1)

    # Wall budget.
    model.Add(sum(wall_vars.values()) <= max_walls)

    # Separation: difference in inside across an edge implies a wall on that edge.
    handled_edges: set[Tuple[Coord, Coord]] = set()
    for u in adjacency:
        for v in adjacency[u]:
            edge = tuple(sorted((u, v)))
            if edge in handled_edges:
                continue
            handled_edges.add(edge)
            model.Add(inside_vars[u] - inside_vars[v] <= wall_vars[u] + wall_vars[v])
            model.Add(inside_vars[v] - inside_vars[u] <= wall_vars[u] + wall_vars[v])

    # Connectivity via flow from horse to inside tiles.
    big_m = len(candidates) + 1
    flow_vars: Dict[Tuple[Coord, Coord], cp_model.IntVar] = {}
    for u in adjacency:
        for v in adjacency[u]:
            flow_vars[(u, v)] = model.NewIntVar(0, big_m, f"f_{u}_{v}")
            model.Add(flow_vars[(u, v)] <= big_m * inside_vars[u])
            model.Add(flow_vars[(u, v)] <= big_m * (1 - wall_vars[u]))

    total_inside = sum(inside_vars[c] for c in candidates if c != root)
    for node in candidates:
        incoming = sum(flow_vars[(u, v)] for (u, v) in flow_vars if v == node)
        outgoing = sum(flow_vars[(u, v)] for (u, v) in flow_vars if u == node)
        if node == root:
            model.Add(outgoing - incoming == total_inside)
        else:
            model.Add(incoming - outgoing == inside_vars[node])

    # Objective.
    cherry_bonus = sum(3 * inside_vars[c] for c in map_data.cherries)
    model.Maximize(sum(inside_vars.values()) + cherry_bonus)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    status_map = {
        cp_model.OPTIMAL: "Optimal",
        cp_model.FEASIBLE: "Feasible",
        cp_model.INFEASIBLE: "Infeasible",
        cp_model.MODEL_INVALID: "ModelInvalid",
        cp_model.UNKNOWN: "Unknown",
    }
    status_str = status_map.get(status, "Unknown")

    assignments: Dict[Coord, Assignment] = {}
    for coord in candidates:
        if solver.Value(wall_vars[coord]) >= 1:
            assignments[coord] = "wall"
        elif solver.Value(inside_vars[coord]) >= 1:
            assignments[coord] = "pasture"
        else:
            assignments[coord] = "grass"

    objective_value = solver.ObjectiveValue() if status in (cp_model.OPTIMAL, cp_model.FEASIBLE) else None
    return SolverResult(status=status_str, objective=objective_value, assignments=assignments)
