import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from .cp_sat_solver import solve_cp_sat, solve_cp_sat_reachability
from .image_parser import calibrate_color_stats_multi, classify_image, load_stats, map_to_string, save_stats
from .ilp_solver import solve_ilp
from .parser import parse_map_file
from .viz import display_solution, save_solution_plot


def _build_solve_parser(parser: argparse.ArgumentParser) -> None:
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


def _build_calibrate_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--images-dir",
        default="images",
        help="Directory containing input screenshots (default: images).",
    )
    parser.add_argument(
        "--maps-dir",
        default="maps",
        help="Directory containing map text files (default: maps).",
    )
    parser.add_argument(
        "--output",
        default="data/tile_color_stats.json",
        help="Output path for calibration stats JSON (default: data/tile_color_stats.json).",
    )
    parser.add_argument(
        "--package-output",
        default=None,
        help="Optional output path for packaged calibration stats (e.g. src/enclose_horse/data/tile_color_stats.json).",
    )
    parser.add_argument(
        "--crop-ratio",
        type=float,
        default=0.6,
        help="Crop ratio for per-tile sampling (default: 0.6).",
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    args = list(argv) if argv is not None else sys.argv[1:]
    if args[:1] == ["calibrate"]:
        parser = argparse.ArgumentParser(description="Horse enclosure solver calibration.")
        _build_calibrate_parser(parser)
        ns = parser.parse_args(args[1:])
        ns.command = "calibrate"
        return ns
    if args[:1] == ["solve"]:
        parser = argparse.ArgumentParser(description="Horse enclosure ILP solver.")
        _build_solve_parser(parser)
        ns = parser.parse_args(args[1:])
        ns.command = "solve"
        return ns

    parser = argparse.ArgumentParser(description="Horse enclosure ILP solver.")
    _build_solve_parser(parser)
    ns = parser.parse_args(args)
    ns.command = "solve"
    return ns


def _collect_calibration_pairs(images_dir: Path, maps_dir: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for image_path in sorted(images_dir.glob("*.png")):
        map_path = maps_dir / f"{image_path.stem}_map.txt"
        if map_path.exists():
            pairs.append((image_path, map_path))
    return pairs


def _run_calibrate(ns: argparse.Namespace) -> int:
    images_dir = Path(ns.images_dir)
    maps_dir = Path(ns.maps_dir)
    pairs = _collect_calibration_pairs(images_dir, maps_dir)
    if not pairs:
        raise ValueError(f"No image/map pairs found in {images_dir} and {maps_dir}.")
    stats = calibrate_color_stats_multi(pairs, crop_ratio=ns.crop_ratio)
    output_path = Path(ns.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    save_stats(stats, output_path)
    print(f"Wrote calibration stats to {output_path}")
    if ns.package_output:
        package_path = Path(ns.package_output)
        package_path.parent.mkdir(parents=True, exist_ok=True)
        save_stats(stats, package_path)
        print(f"Wrote packaged calibration stats to {package_path}")
    return 0


def main(args: Optional[argparse.Namespace] = None) -> int:
    ns = args or parse_args()
    if getattr(ns, "command", "solve") == "calibrate":
        return _run_calibrate(ns)
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
