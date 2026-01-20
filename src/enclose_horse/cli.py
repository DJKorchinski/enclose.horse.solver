import argparse
from pathlib import Path
from typing import Optional

from .cp_sat_solver import solve_cp_sat, solve_cp_sat_reachability
from .image_parser import classify_image, load_stats, map_to_string
from .ilp_solver import solve_ilp
from .parser import parse_map_file
from .viz import display_solution, save_solution_plot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Horse enclosure ILP solver.")
    src_group = parser.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--map", dest="map_path", help="Path to map text file.")
    src_group.add_argument("--image", dest="image_path", help="Path to screenshot to parse.")
    parser.add_argument("--max-walls", type=int, default=13, help="Maximum walls available.")
    parser.add_argument("--plot", dest="plot_path", help="Optional path to save rendered solution PNG.")
    parser.add_argument("--show", action="store_true", help="Display the visualization in a window.")
    parser.add_argument("--write-map", dest="write_map", help="If set, write parsed map text to this path.")
    parser.add_argument(
        "--calibration",
        dest="calibration_path",
        default=None,
        help="Path to saved 6D tile color statistics for image parsing (default: bundled calibration stats).",
    )
    parser.add_argument(
        "--solver",
        choices=["ilp", "cp-sat", "cp-sat-2"],
        default="cp-sat",
        help="Solver backend and strategy to use (default: cp-sat, note: cp-sat-2 has a bug related to connectivity and is not recommended).",
    )
    return parser.parse_args()


def main(args: Optional[argparse.Namespace] = None) -> int:
    ns = args or parse_args()
    if ns.map_path:
        map_data = parse_map_file(ns.map_path)
    else:
        models, scale = load_stats(ns.calibration_path)
        map_data, _ = classify_image(ns.image_path, models, scale)
        if ns.write_map:
            Path(ns.write_map).write_text(map_to_string(map_data))
            print(f"Wrote parsed map to {ns.write_map}")

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
