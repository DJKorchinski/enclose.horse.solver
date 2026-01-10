from typing import Dict, Iterable, List, Set, Tuple

from .parser import Coord, MapData, Tile


def candidate_tiles(map_data: MapData) -> Set[Coord]:
    """Return coordinates that can be decided by the solver (non-water and non-horse)."""
    coords: Set[Coord] = set()
    for r, c, tile in map_data.tiles():
        if tile not in {Tile.WATER, Tile.HORSE}:
            coords.add((r, c))
    return coords


def build_adjacency(map_data: MapData) -> Dict[Coord, List[Coord]]:
    """Adjacency for edge-neighboring candidate tiles, plus portals linking identical IDs."""
    candidates = candidate_tiles(map_data)
    adjacency: Dict[Coord, List[Coord]] = {coord: [] for coord in candidates}

    for r, c in candidates:
        for nr, nc in map_data.neighbors(r, c):
            if (nr, nc) in candidates:
                adjacency[(r, c)].append((nr, nc))

    # Portal links: connect all tiles sharing the same portal id.
    for coords in map_data.portals.values():
        for i, src in enumerate(coords):
            if src not in candidates:
                continue
            for dst in coords[i + 1 :]:
                if dst not in candidates:
                    continue
                adjacency[src].append(dst)
                adjacency[dst].append(src)

    return adjacency
