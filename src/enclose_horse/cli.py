import argparse
from pathlib import Path
from typing import Optional

from .cp_sat_solver import solve_cp_sat, solve_cp_sat_reachability
from .ilp_solver import solve_ilp
from .parser import parse_map_file
from .viz import display_solution, save_solution_plot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Horse enclosure ILP solver.")
    parser.add_argument("--map", dest="map_path", required=True, help="Path to map text file.")
    parser.add_argument("--max-walls", type=int, default=13, help="Maximum walls available.")
    parser.add_argument("--plot", dest="plot_path", help="Optional path to save rendered solution PNG.")
    parser.add_argument("--show", action="store_true", help="Display the visualization in a window.")
    parser.add_argument(
        "--solver",
        choices=["ilp", "cp-sat", "cp-sat-2"],
        default="cp-sat-2",
        help="Solver backend and strategy to use (default: ilp).",
    )
    return parser.parse_args()


def main(args: Optional[argparse.Namespace] = None) -> int:
    ns = args or parse_args()
    map_data = parse_map_file(ns.map_path)

    import time as _time
    start_time = _time.time()
    if ns.solver == "cp-sat":
        result = solve_cp_sat(map_data, max_walls=ns.max_walls)
    elif ns.solver == "cp-sat-2":
        result = solve_cp_sat_reachability(map_data, max_walls=ns.max_walls)
    else:
        result = solve_ilp(map_data, max_walls=ns.max_walls)
    end_time = _time.time()
    print(f"Solved in {end_time - start_time:.2f} seconds.")
    print(f"Status: {result.status}")
    print(f"Objective (score): {result.objective}")
    print(f"Walls used: {result.walls_used()} / {ns.max_walls}")
    print(f"Pasture tiles: {result.pasture_tiles()}")

    if ns.plot_path:
        save_solution_plot(map_data, result, ns.plot_path)
        print(f"Saved plot to {ns.plot_path}")
    if ns.show:
        display_solution(map_data, result)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
