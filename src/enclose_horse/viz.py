from typing import Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors as mcolors

from .ilp_solver import SolverResult
from .parser import Coord, MapData, Tile


def _portal_color(portal_id: int) -> str:
    if portal_id == 0:
        return "#7e3ff2"  # purple
    if portal_id == 1:
        return "#dc143c"  # crimson
    return "#00bcd4"  # cyan


def _color_for_tile(tile: Tile, assignment: str | None, portal_id: int | None = None) -> str:
    # Colors: water=blue, grass=green, pasture=yellow-green, walls=light grey, horse=brown.
    palette: Dict[str, str] = {
        "water": "#4f8dd6",
        "grass": "#7fbf7f",
        "pasture": "#d8e85b",
        "wall": "#c0c0c0",
        "horse": "#8b4513",
    }
    if tile == Tile.PORTAL and portal_id is not None:
        return _portal_color(portal_id)
    if tile == Tile.WATER:
        return palette["water"]
    if tile == Tile.HORSE:
        return palette["horse"]
    if assignment is None:
        return palette["grass"]
    return palette[assignment]


def render_solution(map_data: MapData, result: SolverResult) -> Tuple[plt.Figure, plt.Axes]:
    # Build RGBA float grid for imshow (matplotlib rejects object dtype).
    color_grid = np.zeros((map_data.height, map_data.width, 4), dtype=float)
    for r, c, tile in map_data.tiles():
        assignment = result.assignments.get((r, c))
        portal_id = map_data.portal_ids.get((r, c))
        color_grid[r, c] = mcolors.to_rgba(_color_for_tile(tile, assignment, portal_id))

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(color_grid, origin="upper")

    ax.set_xticks(np.arange(-0.5, map_data.width, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, map_data.height, 1), minor=True)
    ax.grid(which="minor", color="black", linewidth=0.5, alpha=0.4)
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_title("Horse enclosure solution")
    return fig, ax


def save_solution_plot(map_data: MapData, result: SolverResult, output_path: str | None) -> None:
    fig, ax = render_solution(map_data, result)
    if output_path:
        fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)


def display_solution(map_data: MapData, result: SolverResult) -> None:
    fig, ax = render_solution(map_data, result)
    plt.show()
    plt.close(fig)
