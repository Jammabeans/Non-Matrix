from __future__ import annotations

import math


def _seed_template_coords(text: str) -> set[tuple[int, int]]:
    coords: set[tuple[int, int]] = set()
    for row_index, byte in enumerate(text.encode("utf-8")):
        for bit_index in range(8):
            if byte & (1 << (7 - bit_index)):
                coords.add((bit_index, row_index))
    return coords


def coherence_percent(
    structural_coords: set[tuple[int, int]],
    seed_text: str,
    seed_history: list[tuple[str, tuple[int, int]]],
) -> float:
    return coherence_percent_active(structural_coords, seed_text, seed_history)


def coherence_percent_active(
    active_coords: set[tuple[int, int]],
    seed_text: str,
    seed_history: list[tuple[str, tuple[int, int]]],
) -> float:
    if not seed_text:
        return 0.0
    if not active_coords:
        return 0.0
    template_local = _seed_template_coords(seed_text)
    if not template_local:
        return 0.0
    origin = seed_history[-1][1] if seed_history else (0, 0)
    template_global = {(x + origin[0], y + origin[1]) for x, y in template_local}
    overlap = len(active_coords & template_global)
    if overlap == 0:
        # Noise floor for completely non-matching active structures.
        return 10.0

    precision = overlap / max(1, len(active_coords))
    recall = overlap / max(1, len(template_global))
    # Geometric mean strongly penalizes lopsided/mismatched shapes.
    score = (precision * recall) ** 0.5
    return max(0.0, min(100.0, score * 100.0))


def skeleton_pulse_alpha(total_energy: int, tick: int) -> int:
    energy_norm = max(0.0, min(1.0, total_energy / 50_000.0))
    speed = 0.02 + (0.04 * energy_norm)
    wave = (math.sin(tick * speed) + 1.0) * 0.5
    return int(100 + (wave * 155))

