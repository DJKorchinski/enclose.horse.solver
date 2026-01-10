from pathlib import Path

from enclose_horse.parser import Tile, parse_map_file


def test_parse_example_map():
    root = Path(__file__).resolve().parents[1]
    map_data = parse_map_file(root / "example_map.txt")

    assert map_data.width == 21
    assert map_data.height == 21
    assert map_data.horse == (10, 10)

    water_tiles = sum(1 for _, _, tile in map_data.tiles() if tile == Tile.WATER)
    assert water_tiles > 0  # sanity check that water is present
