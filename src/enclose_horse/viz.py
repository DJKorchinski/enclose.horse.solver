from typing import Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np

from .ilp_solver import SolverResult
from .parser import Coord, MapData, Tile


def _color_for_tile(tile: Tile, assignment: str | None) -> str:
    # Colors: water=blue, grass=green, pasture=yellow-green, walls=light grey, horse=brown.
    palette: Dict[str, str] = {
        "water": "#4f8dd6",
        "grass": "#7fbf7f",
        "pasture": "#d8e85b",
        "wall": "#c0c0c0",
        "horse": "#8b4513",
    }
    if tile == Tile.WATER:
        return palette["water"]
    if tile == Tile.HORSE:
        return palette["horse"]
    if assignment is None:
        return palette["grass"]
    return palette[assignment]


def render_solution(map_data: MapData, result: SolverResult) -> Tuple[plt.Figure, plt.Axes]:
    color_grid = np.empty((map_data.height, map_data.width), dtype=object)
    for r, c, tile in map_data.tiles():
        assignment = result.assignments.get((r, c))
        color_grid[r, c] = _color_for_tile(tile, assignment)

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
