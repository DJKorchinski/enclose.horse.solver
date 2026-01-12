from pathlib import Path

from enclose_horse.cp_sat_solver import solve_cp_sat, solve_cp_sat_reachability
from enclose_horse.ilp_solver import solve_ilp
from enclose_horse.parser import parse_map_file

ROOT = Path(__file__).resolve().parents[1]
MAP_CASES = [
    ("example_map.txt", 13, 103),
    ("portal_map.txt", 10, 94),
    ("cherry_map.txt", 12, 66),
    ("portal2_map.txt", 12, 204),
    ("enclosure_map.txt", 2, 2),
    ("enclosure_map2.txt", 2, 2),
]


def _assert_solver_hits_optimum(solver_fn):
    for fname, walls, objective in MAP_CASES:
        map_data = parse_map_file(ROOT / fname)
        result = solver_fn(map_data, max_walls=walls)

        assert result.status.lower() in {"optimal", "feasible"}
        assert round(result.objective) == objective
        assert result.walls_used() <= walls


def test_ilp_matches_optima():
    _assert_solver_hits_optimum(solve_ilp)


def test_cp_sat_matches_optima():
    _assert_solver_hits_optimum(solve_cp_sat)


def test_cp_sat_reachability_matches_optima():
    _assert_solver_hits_optimum(solve_cp_sat_reachability)
