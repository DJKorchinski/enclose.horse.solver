from pathlib import Path

from enclose_horse.parser import Tile, parse_map_file


def test_parse_example_map():
    root = Path(__file__).resolve().parents[1]
    map_data = parse_map_file(root / "maps" / "example_map.txt")

    assert map_data.width == 21
    assert map_data.height == 21
    assert map_data.horse == (10, 10)

    water_tiles = sum(1 for _, _, tile in map_data.tiles() if tile == Tile.WATER)
    assert water_tiles > 0  # sanity check that water is present


def test_parse_portal_map():
    root = Path(__file__).resolve().parents[1]
    map_data = parse_map_file(root / "maps" / "portal_map.txt")

    assert map_data.portals[0] == [(13, 4), (13, 10)]  # coordinates of portal id 0
    assert map_data.horse == (13, 12)


def test_parse_cherry_map():
    root = Path(__file__).resolve().parents[1]
    map_data = parse_map_file(root / "maps" / "cherry_map.txt")

    assert len(map_data.cherries) == 10
    assert map_data.horse == (7, 6)


def test_parse_2026_01_15_map():
    root = Path(__file__).resolve().parents[1]
    map_data = parse_map_file(root / "maps" / "2026.01.15_map.txt")

    assert map_data.width == 23
    assert map_data.height == 19
    assert map_data.horse == (9, 11)
    assert sorted(map_data.portals.keys()) == [0, 1, 2, 3, 4, 5]
    assert all(len(coords) == 2 for coords in map_data.portals.values())
