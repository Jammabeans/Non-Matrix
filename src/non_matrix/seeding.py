from __future__ import annotations

from .cell import Coord
from .sparse_grid import SparseGrid


def seed_text_utf8(
    grid: SparseGrid,
    text: str,
    origin: Coord = (0, 0),
    row_stride: int = 1,
) -> set[Coord]:
    """Seed UTF-8 bytes as an 8-bit row pattern per byte.

    Each byte is mapped left-to-right (MSB to LSB) across 8 columns.
    A set bit activates a cell. Parent links follow activation scan order.
    """
    ox, oy = origin
    grid.register_seed_anchor(origin)
    raw = text.encode("utf-8")
    activated: set[Coord] = set()
    previous: Coord | None = None

    for row_index, byte in enumerate(raw):
        y = oy + row_index * row_stride
        for bit_index in range(8):
            mask = 1 << (7 - bit_index)
            if (byte & mask) == 0:
                continue
            coord = (ox + bit_index, y)
            grid.activate(coord, parent=previous)
            activated.add(coord)
            previous = coord

    return activated


def seed_single_root(grid: SparseGrid, coord: Coord) -> None:
    """Activate a single root coordinate."""
    grid.register_seed_anchor(coord)
    grid.activate(coord)

