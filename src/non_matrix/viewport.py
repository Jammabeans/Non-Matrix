from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Viewport:
    width: int = 1200
    height: int = 800
    cell_size: float = 12.0
    min_cell_size: float = 2.0
    max_cell_size: float = 48.0
    offset_x: float = 0.0
    offset_y: float = 0.0

    def world_to_screen(self, wx: int, wy: int) -> tuple[int, int]:
        sx = int((wx * self.cell_size) + self.offset_x + self.width / 2)
        sy = int((wy * self.cell_size) + self.offset_y + self.height / 2)
        return sx, sy

    def screen_to_world(self, sx: int, sy: int) -> tuple[int, int]:
        wx = int((sx - self.offset_x - self.width / 2) / self.cell_size)
        wy = int((sy - self.offset_y - self.height / 2) / self.cell_size)
        return wx, wy

    def pan(self, dx: float, dy: float) -> None:
        self.offset_x += dx
        self.offset_y += dy

    def zoom_at(self, amount: float, anchor_sx: int, anchor_sy: int) -> None:
        old_size = self.cell_size
        new_size = max(self.min_cell_size, min(self.max_cell_size, old_size * amount))
        if new_size == old_size:
            return

        world_x_before = (anchor_sx - self.offset_x - self.width / 2) / old_size
        world_y_before = (anchor_sy - self.offset_y - self.height / 2) / old_size

        self.cell_size = new_size

        self.offset_x = anchor_sx - (world_x_before * new_size) - self.width / 2
        self.offset_y = anchor_sy - (world_y_before * new_size) - self.height / 2

