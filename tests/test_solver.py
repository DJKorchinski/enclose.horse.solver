from pathlib import Path

from enclose_horse.ilp_solver import solve_ilp
from enclose_horse.parser import parse_map_file


def test_solver_finds_feasible_solution():
    root = Path(__file__).resolve().parents[1]
    map_data = parse_map_file(root / "example_map.txt")
    result = solve_ilp(map_data, max_walls=13)

    assert result.status.lower() in {"optimal", "feasible"}
    assert result.objective is not None and result.objective >= 1
    assert result.walls_used() <= 13
    assert result.pasture_tiles() >= 0
