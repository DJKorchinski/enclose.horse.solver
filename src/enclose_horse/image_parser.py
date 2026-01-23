from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
from PIL import Image

from .parser import MapData, Tile, parse_map_file


@dataclass
class GridDetection:
    offset_x: int
    offset_y: int
    pitch_x: int
    pitch_y: int
    cols: int
    rows: int

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        width = self.cols * self.pitch_x
        height = self.rows * self.pitch_y
        return self.offset_x, self.offset_y, width, height


def _load_image(path: Path | str) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    return np.asarray(img).astype(np.float32) / 255.0


def _dominant_period(profile: np.ndarray, min_period: int = 30, max_period: int = 100) -> int:
    profile = profile - profile.mean()
    spectrum = np.abs(np.fft.rfft(profile))
    spectrum[0] = 0.0
    if spectrum.size < 2 or spectrum.max() == 0:
        return 0
    freqs = np.arange(spectrum.shape[0])
    periods = np.divide(len(profile), freqs, out=np.zeros_like(freqs, dtype=float), where=freqs != 0)
    mask = (periods >= min_period) & (periods <= max_period)
    scores = spectrum * periods
    scores[~mask] = 0.0
    if scores.max() == 0:
        peak_idx = spectrum.argmax()
        if peak_idx == 0:
            return 0
        return round(len(profile) / peak_idx)
    peak_idx = scores.argmax()
    return round(periods[peak_idx])


def _best_offset_and_count(
    profile: np.ndarray, pitch: int, min_count: int = 15, max_count: int = 30
) -> Tuple[int, int, float]:
    if pitch <= 0:
        return 0, max(min_count, 1), -1.0
    best_offset = 0
    best_count = max(min_count, 1)
    best_score = -1.0
    for offset in range(0, pitch):
        for count in range(min_count, max_count + 1):
            positions = offset + np.arange(count) * pitch
            positions = positions[positions < len(profile)]
            if positions.size == 0:
                continue
            idx = np.clip(np.rint(positions).astype(int), 0, len(profile) - 1)
            score = profile[idx].sum() + 0.1 * positions.size
            if score > best_score:
                best_score = score
                best_offset = offset
                best_count = positions.size
    return best_offset, best_count, best_score


def detect_grid(image: np.ndarray) -> GridDetection:
    """Detect grid spacing and offsets using gradient projections."""
    gray = image.mean(axis=2)
    grad_x = np.abs(np.diff(gray, axis=1))  # vertical lines cause horizontal gradients
    grad_y = np.abs(np.diff(gray, axis=0))  # horizontal lines cause vertical gradients

    vert_profile = grad_x.mean(axis=0)
    horiz_profile = grad_y.mean(axis=1)

    pitch_x = _dominant_period(vert_profile)
    pitch_y = _dominant_period(horiz_profile)
    if pitch_x <= 0 or pitch_y <= 0:
        raise ValueError("Failed to detect grid period.")

    def _search(profile: np.ndarray, base_pitch: int) -> Tuple[int, int, int]:
        best = (0, 0, 0, -1.0)  # pitch, offset, count, score
        for cand_pitch in range(max(30, base_pitch - 6), min(100, base_pitch + 7)):
            off, count, score = _best_offset_and_count(profile, cand_pitch)
            if score > best[3]:
                best = (cand_pitch, off, count, score)
        # also try double pitch to avoid halving the grid
        double_pitch = min(120, base_pitch * 2)
        off_double, count_double, score_double = _best_offset_and_count(profile, double_pitch)
        if score_double > best[3]:
            best = (double_pitch, off_double, count_double, score_double)
        return best[0], best[1], best[2]

    pitch_x, offset_x, cols = _search(vert_profile, pitch_x)
    pitch_y, offset_y, rows = _search(horiz_profile, pitch_y)
    cols = max(1, round((image.shape[1] - 2 * offset_x) / pitch_x))
    rows = max(1, round((image.shape[0] - 2 * offset_y) / pitch_y))
    return GridDetection(offset_x, offset_y, pitch_x, pitch_y, cols, rows)


def _cell_patch(image: np.ndarray, grid: GridDetection, row: int, col: int, crop_ratio: float) -> np.ndarray:
    y0 = grid.offset_y + row * grid.pitch_y
    x0 = grid.offset_x + col * grid.pitch_x
    y1 = min(grid.offset_y + (row + 1) * grid.pitch_y, image.shape[0])
    x1 = min(grid.offset_x + (col + 1) * grid.pitch_x, image.shape[1])
    dy = int(grid.pitch_y * (1 - crop_ratio) / 2)
    dx = int(grid.pitch_x * (1 - crop_ratio) / 2)
    patch = image[y0 + dy : max(y0 + dy, y1 - dy), x0 + dx : max(x0 + dx, x1 - dx)]
    if patch.size == 0:
        # Fallback to minimal 1x1 slice to avoid empty patches in extreme edge cases.
        patch = image[max(0, y0) : min(image.shape[0], y0 + 1), max(0, x0) : min(image.shape[1], x0 + 1)]
    return patch


def _features(patch: np.ndarray) -> np.ndarray:
    flat = patch.reshape(-1, 3)
    mean = flat.mean(axis=0)
    var = flat.var(axis=0)
    return np.concatenate([mean, var])


def _collect_calibration_features(
    image_path: Path | str, map_path: Path | str, crop_ratio: float
) -> Dict[str, List[np.ndarray]]:
    image = _load_image(image_path)
    map_data = parse_map_file(map_path)
    grid = detect_grid(image)

    # If grid detection is close but not exact, force rows/cols to map shape.
    grid = GridDetection(
        offset_x=grid.offset_x,
        offset_y=grid.offset_y,
        pitch_x=grid.pitch_x,
        pitch_y=grid.pitch_y,
        cols=map_data.width,
        rows=map_data.height,
    )

    buckets: Dict[str, List[np.ndarray]] = {}
    for r in range(map_data.height):
        for c in range(map_data.width):
            patch = _cell_patch(image, grid, r, c, crop_ratio)
            feat = _features(patch)
            tile = map_data.grid[r][c]
            if tile == Tile.PORTAL:
                key = f"portal_{map_data.portal_ids[(r, c)]}"
            else:
                key = tile.value
            buckets.setdefault(key, []).append(feat)
    return buckets


def calibrate_color_stats_multi(
    pairs: Iterable[Tuple[Path | str, Path | str]], crop_ratio: float = 0.6
) -> Dict[str, List[float]]:
    """Compute 6D (mean+var) color stats per tile using multiple image/map pairs."""
    merged: Dict[str, List[np.ndarray]] = {}
    all_feats: List[np.ndarray] = []
    for image_path, map_path in pairs:
        buckets = _collect_calibration_features(image_path, map_path, crop_ratio)
        for key, feats in buckets.items():
            merged.setdefault(key, []).extend(feats)
            all_feats.extend(feats)

    if not merged:
        raise ValueError("No calibration pairs provided.")

    stats: Dict[str, List[float]] = {}
    for key, feats in merged.items():
        mat = np.stack(feats, axis=0)
        stats[key] = mat.mean(axis=0).tolist()

    # Feature-wise scale so each dimension contributes similarly.
    stacked = np.stack(all_feats, axis=0)
    scale = stacked.std(axis=0)
    scale[scale < 1e-6] = 1e-3
    stats["_scale"] = scale.tolist()
    return stats


def calibrate_color_stats(image_path: Path | str, map_path: Path | str, crop_ratio: float = 0.6) -> Dict[str, List[float]]:
    """Compute 6D (mean+var) color stats per tile using a labeled image and map."""
    return calibrate_color_stats_multi([(image_path, map_path)], crop_ratio=crop_ratio)


def save_stats(stats: Dict[str, List[float]], path: Path | str) -> None:
    Path(path).write_text(json.dumps(stats, indent=2))


def _load_default_stats_text() -> str:
    try:
        return resources.files("enclose_horse").joinpath("data/tile_color_stats.json").read_text()
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            "Default calibration stats not found; pass --calibration PATH or reinstall the package."
        ) from exc


def load_stats(path: Path | str | None = None) -> Tuple[Dict[str, np.ndarray], np.ndarray]:
    if path is None:
        data_text = _load_default_stats_text()
    else:
        data_text = Path(path).read_text()
    data = json.loads(data_text)
    scale = np.asarray(data.get("_scale", [1.0] * 6), dtype=np.float32)
    prototypes = {k: np.asarray(v, dtype=np.float32) for k, v in data.items() if k != "_scale"}
    return prototypes, scale


def _nearest_label(feat: np.ndarray, models: Dict[str, np.ndarray], scale: np.ndarray) -> str:
    best = None
    best_dist = float("inf")
    for label, proto in models.items():
        diff = (feat - proto) / scale
        dist = np.linalg.norm(diff)
        if dist < best_dist:
            best = label
            best_dist = dist
    return best or "."


def classify_image(
    image_path: Path | str, models: Dict[str, np.ndarray], scale: np.ndarray, crop_ratio: float = 0.6
) -> Tuple[MapData, np.ndarray]:
    """Parse an image into MapData using calibrated color models."""
    image = _load_image(image_path)
    grid = detect_grid(image)

    labels: List[List[str]] = []
    brightness: List[Tuple[float, Tuple[int, int], str]] = []
    predicted_horses: List[Tuple[float, Tuple[int, int]]] = []
    for r in range(grid.rows):
        row_labels: List[str] = []
        for c in range(grid.cols):
            patch = _cell_patch(image, grid, r, c, crop_ratio)
            feat = _features(patch)
            label = _nearest_label(feat, models, scale)
            row_labels.append(label)
            bright = float(patch.max())
            brightness.append((bright, (r, c), label))
            if label == Tile.HORSE.value:
                predicted_horses.append((bright, (r, c)))
        labels.append(row_labels)

    # Enforce a single horse by preferring cells classified as horse; otherwise brightest.
    if predicted_horses:
        horse_r, horse_c = max(predicted_horses, key=lambda t: t[0])[1]
    else:
        horse_r, horse_c = max(brightness, key=lambda t: t[0])[1] if brightness else (0, 0)
    for r in range(grid.rows):
        for c in range(grid.cols):
            if (r, c) == (horse_r, horse_c):
                labels[r][c] = Tile.HORSE.value
            elif labels[r][c] == Tile.HORSE.value:
                labels[r][c] = Tile.GRASS.value

    portals: Dict[int, List[Tuple[int, int]]] = {}
    portal_ids: Dict[Tuple[int, int], int] = {}
    cherries: List[Tuple[int, int]] = []
    golden_apples: List[Tuple[int, int]] = []
    bees: List[Tuple[int, int]] = []
    horse: Tuple[int, int] | None = None

    for r in range(grid.rows):
        for c in range(grid.cols):
            label = labels[r][c]
            if label.startswith("portal_"):
                pid = int(label.split("_")[1])
                portals.setdefault(pid, []).append((r, c))
                portal_ids[(r, c)] = pid
                labels[r][c] = Tile.PORTAL.value
            elif label == Tile.CHERRY.value:
                cherries.append((r, c))
            elif label == Tile.GOLDEN_APPLE.value:
                golden_apples.append((r, c))
            elif label == Tile.BEE.value:
                bees.append((r, c))
            elif label == Tile.HORSE.value:
                horse = (r, c)

    if horse is None:
        raise ValueError("Horse not detected in screenshot.")

    grid_tiles: List[List[Tile]] = []
    for r in range(grid.rows):
        row: List[Tile] = []
        for c in range(grid.cols):
            ch = labels[r][c]
            row.append(Tile(ch) if ch in {t.value for t in Tile} else Tile.GRASS)
        grid_tiles.append(row)

    map_data = MapData(
        grid=grid_tiles,
        width=grid.cols,
        height=grid.rows,
        horse=horse,
        portals=portals,
        portal_ids=portal_ids,
        cherries=cherries,
        golden_apples=golden_apples,
        bees=bees,
    )
    return map_data, image


def map_to_string(map_data: MapData) -> str:
    lines: List[str] = []
    for r in range(map_data.height):
        line_chars: List[str] = []
        for c in range(map_data.width):
            tile = map_data.grid[r][c]
            if tile == Tile.PORTAL:
                line_chars.append(str(map_data.portal_ids[(r, c)]))
            else:
                line_chars.append(tile.value)
        lines.append("".join(line_chars))
    return "\n".join(lines)
