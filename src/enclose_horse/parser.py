from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, List, Tuple


class Tile(str, Enum):
    WATER = "~"
    GRASS = "."
    HORSE = "H"


Coord = Tuple[int, int]


@dataclass(frozen=True)
class MapData:
    grid: List[List[Tile]]
    width: int
    height: int
    horse: Coord

    def neighbors(self, row: int, col: int) -> Iterable[Coord]:
        deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dr, dc in deltas:
            nr, nc = row + dr, col + dc
            if 0 <= nr < self.height and 0 <= nc < self.width:
                yield nr, nc

    def tiles(self) -> Iterable[Tuple[int, int, Tile]]:
        for r in range(self.height):
            for c in range(self.width):
                yield r, c, self.grid[r][c]


def parse_map_file(path: Path | str) -> MapData:
    raw_lines = [line.rstrip("\n") for line in Path(path).read_text().splitlines()]
    if not raw_lines:
        raise ValueError("Map is empty.")

    width = len(raw_lines[0])
    grid: List[List[Tile]] = []
    horse: Coord | None = None

    for row_idx, line in enumerate(raw_lines):
        if len(line) != width:
            raise ValueError(f"Inconsistent row width at line {row_idx}: expected {width}, got {len(line)}")

        row: List[Tile] = []
        for col_idx, ch in enumerate(line):
            if ch == Tile.WATER.value:
                row.append(Tile.WATER)
            elif ch == Tile.GRASS.value:
                row.append(Tile.GRASS)
            elif ch == Tile.HORSE.value:
                if horse is not None:
                    raise ValueError("Multiple horses found in map.")
                horse = (row_idx, col_idx)
                row.append(Tile.HORSE)
            else:
                raise ValueError(f"Unexpected tile '{ch}' at {(row_idx, col_idx)}")
        grid.append(row)

    if horse is None:
        raise ValueError("No horse tile found in map.")

    return MapData(grid=grid, width=width, height=len(grid), horse=horse)
