from __future__ import annotations

import random
from dataclasses import dataclass
from collections.abc import Iterator

from .cell import Coord, MAX_ENERGY

MAX_CELLS = 10_000
MAX_RADIUS = 500

MOORE_OFFSETS: tuple[Coord, ...] = (
    (-1, -1),
    (0, -1),
    (1, -1),
    (-1, 0),
    (1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
)


@dataclass(slots=True)
class Meta:
    mutation_type: int = 0
    energy: int = MAX_ENERGY
    parent: Coord | None = None
    last_touched_tick: int = 0
    isolated_ticks: int = 0


class SparseGrid:
    """Coordinate-only sparse grid with optional metadata for active/changing cells."""

    def __init__(
        self,
        mutation_chance: float = 0.05,
        rng: random.Random | None = None,
        max_active_cells: int = 20_000,
    ) -> None:
        self.cells: set[Coord] = set()
        self.alive_coords: set[Coord] = self.cells
        self.meta: dict[Coord, Meta] = {}
        self.active_cells: set[Coord] = set()
        self.static_ticks: dict[Coord, int] = {}
        self.survival_ticks: dict[Coord, int] = {}
        self.pending_death: set[Coord] = set()
        self.tick: int = 0
        self.mutation_chance = mutation_chance
        self.rng = rng if rng is not None else random.Random(0)
        self.max_active_cells = max_active_cells
        self.seed_anchors: set[Coord] = set()
        self.anchor_radius: int = 5
        self.cooldown_ticks: int = 0
        self.pending_heat_dump: bool = False
        self.occupancy_ticks: dict[Coord, int] = {}
        self.structural_cells: set[Coord] = set()
        self.structural_mutation: dict[Coord, int] = {}
        self.coherence_match: bool = False

    def get(self, coord: Coord) -> Meta | None:
        return self.meta.get(coord)

    def _get_or_create_meta(self, coord: Coord) -> Meta:
        meta = self.meta.get(coord)
        if meta is None:
            meta = Meta(last_touched_tick=self.tick)
            self.meta[coord] = meta
        return meta

    def ensure_awake_metadata(self, coord: Coord) -> None:
        """Rehydrate metadata for active thinkers that were compacted away."""
        if coord not in self.cells or coord in self.meta or coord not in self.active_cells:
            return
        self.meta[coord] = Meta(
            mutation_type=self.rng.randrange(8),
            energy=MAX_ENERGY,
            last_touched_tick=self.tick,
        )

    def mutation_type(self, coord: Coord) -> int:
        meta = self.meta.get(coord)
        return 0 if meta is None else meta.mutation_type

    def is_structural(self, coord: Coord) -> bool:
        return coord in self.structural_cells

    def max_energy(self, coord: Coord) -> int:
        return MAX_ENERGY * 5 if self.is_structural(coord) else MAX_ENERGY

    def set_mutation_type(self, coord: Coord, mutation_type: int) -> None:
        meta = self._get_or_create_meta(coord)
        if coord in self.structural_cells and coord in self.structural_mutation:
            meta.mutation_type = self.structural_mutation[coord]
        else:
            meta.mutation_type = int(mutation_type) & 0b111
        meta.last_touched_tick = self.tick

    def energy(self, coord: Coord) -> int:
        meta = self.meta.get(coord)
        return self.max_energy(coord) if meta is None else meta.energy

    def set_energy(self, coord: Coord, energy: int) -> None:
        meta = self._get_or_create_meta(coord)
        meta.energy = max(0, min(self.max_energy(coord), int(energy)))
        meta.last_touched_tick = self.tick

    def record_occupancy_tick(self, coord: Coord) -> None:
        total = self.occupancy_ticks.get(coord, 0) + 1
        self.occupancy_ticks[coord] = total
        if total >= 250:
            self.structural_cells.add(coord)
            self.structural_mutation.setdefault(coord, self.mutation_type(coord))

    def parent(self, coord: Coord) -> Coord | None:
        meta = self.meta.get(coord)
        return None if meta is None else meta.parent

    def set_parent(self, coord: Coord, parent: Coord | None) -> None:
        if parent is None:
            return
        meta = self._get_or_create_meta(coord)
        if meta.parent is None:
            meta.parent = parent
            meta.last_touched_tick = self.tick

    def last_touched_tick(self, coord: Coord) -> int:
        meta = self.meta.get(coord)
        return self.tick if meta is None else meta.last_touched_tick

    def touch(self, coord: Coord) -> None:
        meta = self._get_or_create_meta(coord)
        meta.last_touched_tick = self.tick

    def isolated_ticks(self, coord: Coord) -> int:
        meta = self.meta.get(coord)
        return 0 if meta is None else meta.isolated_ticks

    def set_isolated_ticks(self, coord: Coord, value: int) -> None:
        meta = self._get_or_create_meta(coord)
        meta.isolated_ticks = max(0, int(value))
        meta.last_touched_tick = self.tick

    def ensure(self, coord: Coord, parent: Coord | None = None) -> Coord:
        if coord not in self.cells:
            self.cells.add(coord)
        if parent is not None:
            self.set_parent(coord, parent)
        return coord

    def activate(self, coord: Coord, parent: Coord | None = None, force_inherit: bool = False) -> Coord:
        was_missing = coord not in self.cells
        self.ensure(coord, parent=parent)
        self.pending_death.discard(coord)

        if was_missing:
            inherited_mutation = 0
            has_parent_lineage = False
            inherited_energy = MAX_ENERGY
            if parent is not None:
                if parent in self.cells:
                    inherited_mutation = self.mutation_type(parent)
                    inherited_energy = self.energy(parent)
                    has_parent_lineage = True

            if has_parent_lineage and not force_inherit and self.rng.random() < self.mutation_chance:
                inherited_mutation ^= 1 << self.rng.randrange(3)
                inherited_energy = MAX_ENERGY

            self.set_mutation_type(coord, inherited_mutation)
            self.set_energy(coord, inherited_energy)
            if coord in self.structural_cells:
                self.set_energy(coord, self.max_energy(coord))

        self.cells.add(coord)
        self.mark_active(coord, include_neighbors=True)
        self.static_ticks[coord] = 0
        if was_missing:
            self.survival_ticks[coord] = 0
        self.touch(coord)
        return coord

    def clear(self) -> None:
        self.cells.clear()
        self.meta.clear()
        self.active_cells.clear()
        self.static_ticks.clear()
        self.survival_ticks.clear()
        self.pending_death.clear()
        self.seed_anchors.clear()
        self.cooldown_ticks = 0
        self.pending_heat_dump = False
        self.occupancy_ticks.clear()
        self.structural_cells.clear()
        self.structural_mutation.clear()
        self.coherence_match = False

    def mark_for_death(self, coord: Coord) -> None:
        if coord in self.cells:
            self.pending_death.add(coord)

    def process_pending_deaths(self, limit: int = 500) -> int:
        processed = 0
        for coord in tuple(self.pending_death):
            self.pending_death.discard(coord)
            self.deactivate(coord)
            processed += 1
            if processed >= limit:
                break
        return processed

    def is_old_growth(self, coord: Coord) -> bool:
        return self.survival_ticks.get(coord, 0) >= 100

    def is_within_bounds(self, coord: Coord) -> bool:
        x, y = coord
        return abs(x) <= MAX_RADIUS and abs(y) <= MAX_RADIUS

    def register_seed_anchor(self, origin: Coord) -> None:
        self.seed_anchors.add(origin)

    def is_anchor_protected(self, coord: Coord) -> bool:
        cx, cy = coord
        radius_sq = self.anchor_radius * self.anchor_radius
        for ax, ay in self.seed_anchors:
            dx = cx - ax
            dy = cy - ay
            if (dx * dx) + (dy * dy) <= radius_sq:
                return True
        return False

    def cull_to_max_active(self) -> None:
        protected = {coord for coord in self.cells if self.is_anchor_protected(coord)}
        cullable_count = len(self.cells) - len(protected)
        overflow = len(self.cells) - self.max_active_cells
        if overflow <= 0:
            return
        if cullable_count <= 0:
            return

        oldest_first = sorted(
            (coord for coord in self.cells if coord not in protected),
            key=self.last_touched_tick,
        )
        for coord in oldest_first[: min(overflow, cullable_count)]:
            self.deactivate(coord)

    def deactivate(self, coord: Coord) -> None:
        if coord not in self.cells:
            return
        self.cells.discard(coord)
        self.active_cells.discard(coord)
        self.static_ticks.pop(coord, None)
        self.survival_ticks.pop(coord, None)
        self.meta.pop(coord, None)
        self.mark_active(coord, include_neighbors=True)

    def remove_cell(self, coord: Coord) -> None:
        """Hard-delete a cell from storage regardless of bitfield payload."""
        self.cells.discard(coord)
        self.active_cells.discard(coord)
        self.static_ticks.pop(coord, None)
        self.survival_ticks.pop(coord, None)
        self.meta.pop(coord, None)

    def mark_active(self, coord: Coord, include_neighbors: bool = True) -> None:
        self.active_cells.add(coord)
        if not include_neighbors:
            return
        cx, cy = coord
        for dx, dy in MOORE_OFFSETS:
            self.active_cells.add((cx + dx, cy + dy))

    def alive_neighbors(self, coord: Coord) -> int:
        cx, cy = coord
        total = 0
        for dx, dy in MOORE_OFFSETS:
            if (cx + dx, cy + dy) in self.cells:
                total += 1
        return total

    def iter_alive(self) -> Iterator[Coord]:
        yield from self.cells

    def candidate_frontier(self) -> set[Coord]:
        seeds = self.active_cells if self.active_cells else self.cells
        frontier: set[Coord] = set(seeds)
        for cx, cy in seeds:
            for dx, dy in MOORE_OFFSETS:
                frontier.add((cx + dx, cy + dy))
        return frontier

    def maybe_compact_static_metadata(self) -> None:
        """Forget metadata for cells that are not currently thinking."""
        for coord in tuple(self.cells):
            if coord not in self.active_cells:
                self.meta.pop(coord, None)

