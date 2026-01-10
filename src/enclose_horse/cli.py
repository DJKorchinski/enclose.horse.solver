import argparse
from pathlib import Path
from typing import Optional

from .ilp_solver import solve_ilp
from .parser import parse_map_file
from .viz import display_solution, save_solution_plot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Horse enclosure ILP solver.")
    parser.add_argument("--map", dest="map_path", required=True, help="Path to map text file.")
    parser.add_argument("--max-walls", type=int, default=13, help="Maximum walls available.")
    parser.add_argument("--plot", dest="plot_path", help="Optional path to save rendered solution PNG.")
    parser.add_argument("--show", action="store_true", help="Display the visualization in a window.")
    return parser.parse_args()


def main(args: Optional[argparse.Namespace] = None) -> int:
    ns = args or parse_args()
    map_data = parse_map_file(ns.map_path)
    result = solve_ilp(map_data, max_walls=ns.max_walls)

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
