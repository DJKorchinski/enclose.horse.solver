from pathlib import Path

import pytest
from PIL import Image

from enclose_horse.image_parser import classify_image, load_stats, map_to_string


@pytest.mark.parametrize("name", ["example", "portal2", "rect", "2026.01.15"])
def test_image_parser_tolerates_small_border_offsets(tmp_path, name: str):
    root = Path(__file__).resolve().parents[1]
    img_path = root / "images" / f"{name}.png"
    ref_map = (root / "maps" / f"{name}_map.txt").read_text().strip()
    models, scale = load_stats(root / "data/tile_color_stats.json")

    img = Image.open(img_path)
    width, height = img.size

    for dx in range(4):
        for dy in range(4):
            cropped = img.crop((dx, dy, width, height))
            test_path = tmp_path / f"{name}_{dx}_{dy}.png"
            cropped.save(test_path)

            parsed, _ = classify_image(test_path, models, scale)
            parsed_text = map_to_string(parsed).strip()
            assert parsed_text == ref_map, f"Mismatch at offset ({dx},{dy})"
