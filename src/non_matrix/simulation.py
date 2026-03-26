from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from .rules import step_life
from .seeding import seed_single_root, seed_text_utf8
from .sparse_grid import SparseGrid


@dataclass
class SimulationConfig:
    auto_step: bool = True
    steps_per_second: int = 12


class Simulation:
    def __init__(self, grid: SparseGrid | None = None, config: SimulationConfig | None = None) -> None:
        self.grid = grid if grid is not None else SparseGrid()
        self.config = config if config is not None else SimulationConfig()
        self.peak_population = len(self.grid.alive_coords)
        self.snapshot: set[tuple[int, int]] = set(self.grid.alive_coords)
        self.snapshot_tick: int = self.grid.tick
        self._lock = threading.RLock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._seed_history: list[tuple[str, tuple[int, int]]] = []

    def step(self) -> None:
        with self._lock:
            step_life(self.grid)
            self.peak_population = max(self.peak_population, len(self.grid.alive_coords))
            if self.grid.tick % 5 == 0:
                self.snapshot = set(self.grid.alive_coords)
                self.snapshot_tick = self.grid.tick

    def start_heartbeat(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._thread.start()

    def stop_heartbeat(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def _heartbeat_loop(self) -> None:
        while self._running:
            if self.config.auto_step:
                self.step()
            sleep_for = 1.0 / max(1, self.config.steps_per_second)
            time.sleep(sleep_for)

    def seed_text(self, text: str, origin: tuple[int, int] = (0, 0)) -> set[tuple[int, int]]:
        with self._lock:
            activated = seed_text_utf8(self.grid, text=text, origin=origin)
            self._seed_history.append((text, origin))
            self.peak_population = max(self.peak_population, len(self.grid.alive_coords))
            self.snapshot = set(self.grid.alive_coords)
            self.snapshot_tick = self.grid.tick
            return activated

    def total_energy(self) -> int:
        with self._lock:
            return sum(self.grid.energy(coord) for coord in self.grid.iter_alive())

    def snapshot_coords(self) -> set[tuple[int, int]]:
        with self._lock:
            return set(self.snapshot)

    def clear_world(self) -> None:
        with self._lock:
            self.grid.clear()
            self.snapshot = set()
            self.snapshot_tick = self.grid.tick
            self.peak_population = 0
            self._seed_history.clear()

    def seed_root(self, coord: tuple[int, int]) -> None:
        with self._lock:
            seed_single_root(self.grid, coord)
            self.snapshot = set(self.grid.alive_coords)
            self.snapshot_tick = self.grid.tick

    def mutation_type_at(self, coord: tuple[int, int]) -> int:
        with self._lock:
            return self.grid.mutation_type(coord)

    def parent_at(self, coord: tuple[int, int]) -> tuple[int, int] | None:
        with self._lock:
            return self.grid.parent(coord)

    def last_touched_at(self, coord: tuple[int, int]) -> int:
        with self._lock:
            return self.grid.last_touched_tick(coord)

    def is_old_growth_at(self, coord: tuple[int, int]) -> bool:
        with self._lock:
            return self.grid.is_old_growth(coord)

    def is_structural_at(self, coord: tuple[int, int]) -> bool:
        with self._lock:
            return self.grid.is_structural(coord)

    def structural_count(self) -> int:
        with self._lock:
            return len(self.grid.structural_cells)

    def structural_coords_snapshot(self) -> set[tuple[int, int]]:
        with self._lock:
            return set(self.grid.structural_cells)

    def seed_history_snapshot(self) -> list[tuple[str, tuple[int, int]]]:
        with self._lock:
            return list(self._seed_history)

    def last_seeded_text(self) -> str:
        with self._lock:
            return self._seed_history[-1][0] if self._seed_history else ""

    def set_coherence_match(self, matched: bool) -> None:
        with self._lock:
            self.grid.coherence_match = bool(matched)

