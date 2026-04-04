from __future__ import annotations

import math
import random
from dataclasses import dataclass
from collections.abc import Iterator

from .cell import Coord, MAX_ENERGY
from .modes import SimMode

MAX_CELLS = 25_000
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
    growth_vector: Coord = (0, 0)
    last_touched_tick: int = 0
    isolated_ticks: int = 0


class SparseGrid:
    """Coordinate-only sparse grid with optional metadata for active/changing cells."""

    def __init__(
        self,
        mutation_chance: float = 0.05,
        rng: random.Random | None = None,
        rng_seed: int = 0,
        max_active_cells: int = 20_000,
        min_radius: int = 300,
        max_radius: int = 1200,
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
        self.rng_seed = int(rng_seed)
        self.rng = rng if rng is not None else random.Random(self.rng_seed)
        self.max_active_cells = max_active_cells
        self.seed_anchors: set[Coord] = set()
        self.anchor_radius: int = 5
        self.cooldown_ticks: int = 0
        self.pending_heat_dump: bool = False
        self.occupancy_ticks: dict[Coord, int] = {}
        self.structural_cells: set[Coord] = set()
        self.structural_mutation: dict[Coord, int] = {}
        self.coherence_match: bool = False
        self.min_radius: int = max(1, int(min_radius))
        self.max_radius: int = max(self.min_radius, int(max_radius))
        self.current_radius: int = max(min(MAX_RADIUS, self.max_radius), self.min_radius)
        self.radius_step: int = 50
        self.coherence_high_threshold: float = 70.0
        self.coherence_low_threshold: float = 35.0
        self.coherence_expand_ticks: int = 10
        self.coherence_contract_ticks: int = 20
        self.coherence_high_streak: int = 0
        self.coherence_low_streak: int = 0
        self.last_coherence_percent: float = 0.0
        self.food_spawn_interval: int = 150
        self.food_cluster_min: int = 3
        self.food_cluster_max: int = 6
        self.food_min_distance_ratio: float = 0.35
        self.food_energy_bonus: int = MAX_ENERGY * 4
        self.food_clusters: set[Coord] = set()
        self.outpost_anchors: set[Coord] = set()
        self.overcrowded_structural_cells: set[Coord] = set()
        self.structural_overcrowded_ticks: dict[Coord, int] = {}
        self.food_capture_radius: int = 5
        self.outpost_lock_radius: int = 2
        self.mycelium_target_neighbors: int = 2
        self.mycelium_zero_tax_enabled: bool = True
        self.mycelium_bootstrap_ticks: int = 10
        self.mycelium_bootstrap_crowding_bonus: int = 2
        self.mycelium_bootstrap_energy_discount: float = 0.35
        self.vine_off_target_multiplier: int = 2
        self.crowding_threshold: int = 3
        self.crowding_multiplier: int = 4
        self.structural_discount_factor: float = 0.2
        self.structural_overcrowded_neighbors: int = 2
        self.structural_hibernate_overcrowd_neighbors: int = 4
        self.structural_hibernate_ticks: int = 5
        self.chemotaxis_outer_ratio: float = 0.7
        self.chemotaxis_discount_factor: float = 0.5
        self.outpost_magnet_radius: int = 200
        self.outpost_magnet_discount_factor: float = 0.25
        self.vector_bias_enabled: bool = True
        self.vector_bias_forward_chance: float = 0.75
        self.vector_bias_side_chance: float = 0.25
        self.vector_bias_maturity_ticks: int = 5
        self.vector_cone_degrees: float = 45.0
        self.lateral_inhibition_enabled: bool = True
        self.mode: SimMode = SimMode.MYCELIUM
        self.p_bias: dict[Coord, float] = {}
        self.state: dict[Coord, int] = {}
        self.logic_role: dict[Coord, str] = {}
        self.logic_success_streak: int = 0
        self.logic_solved: bool = False
        self.logic_pause_requested: bool = False
        self.logic_resume_requested: bool = False
        self.logic_stagnation_ticks: int = 0
        self.logic_jolt_notice_ticks: int = 0
        self.logic_solved_cells: set[Coord] = set()
        self.logic_success_streak_ticks: int = 3
        self.logic_jolt_threshold_ticks: int = 20
        self.logic_jolt_bias: float = 0.8
        self.logic_flip_hot_chance: float = 0.95
        self.logic_flip_cold_chance: float = 0.005
        self.logic_gate_hot_chance: float = 0.85
        self.logic_gate_cold_chance: float = 0.01
        self.target_number: int = 35
        self.render_every_x_ticks: int = 5
        self.needs_final_render: bool = False
        self.debug_mycelium_diagnosis: bool = False
        self.debug_mycelium_log_every: int = 20

        # Deterministic exploration fields.
        self.smell_field: dict[Coord, float] = {}
        self.path_memory: dict[Coord, float] = {}
        self.smell_decay: float = 0.93
        self.smell_diffusion: float = 0.22
        self.smell_food_source: float = 8.0
        self.smell_outpost_source: float = 3.0
        self.path_memory_decay: float = 0.9
        self.path_memory_deposit: float = 1.0
        self.score_smell_weight: float = 1.0
        self.score_alignment_weight: float = 0.4
        self.score_memory_penalty_weight: float = 0.7
        self.score_crowding_penalty_weight: float = 0.2

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

    def growth_vector(self, coord: Coord) -> Coord:
        meta = self.meta.get(coord)
        return (0, 0) if meta is None else meta.growth_vector

    def set_growth_vector(self, coord: Coord, vector: Coord) -> None:
        meta = self._get_or_create_meta(coord)
        vx = 0 if vector[0] == 0 else (1 if vector[0] > 0 else -1)
        vy = 0 if vector[1] == 0 else (1 if vector[1] > 0 else -1)
        meta.growth_vector = (vx, vy)
        meta.last_touched_tick = self.tick

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

    def activate(
        self,
        coord: Coord,
        parent: Coord | None = None,
        force_inherit: bool = False,
        growth_vector: Coord | None = None,
    ) -> Coord:
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
            inherited_vector: Coord = (0, 0)
            if growth_vector is not None:
                inherited_vector = growth_vector
            elif parent is not None and parent in self.cells:
                parent_vector = self.growth_vector(parent)
                if parent_vector != (0, 0):
                    inherited_vector = parent_vector
                else:
                    inherited_vector = (coord[0] - parent[0], coord[1] - parent[1])
            self.set_growth_vector(coord, inherited_vector)
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
        self.current_radius = max(min(MAX_RADIUS, self.max_radius), self.min_radius)
        self.coherence_high_streak = 0
        self.coherence_low_streak = 0
        self.last_coherence_percent = 0.0
        self.food_clusters.clear()
        self.outpost_anchors.clear()
        self.overcrowded_structural_cells.clear()
        self.structural_overcrowded_ticks.clear()
        self.smell_field.clear()
        self.path_memory.clear()
        self.p_bias.clear()
        self.state.clear()
        self.logic_role.clear()
        self.logic_success_streak = 0
        self.logic_solved = False
        self.logic_pause_requested = False
        self.logic_resume_requested = False
        self.logic_stagnation_ticks = 0
        self.logic_jolt_notice_ticks = 0
        self.logic_solved_cells.clear()
        self.needs_final_render = False
        self.rng = random.Random(self.rng_seed)

    def _init_logic_lattice(self) -> None:
        """Initialize a dynamic N x N logic loom based on target_number."""
        self.clear()
        self.logic_success_streak = 0
        self.logic_solved = False
        self.logic_pause_requested = False
        self.logic_resume_requested = False
        self.logic_stagnation_ticks = 0
        self.logic_jolt_notice_ticks = 0
        self.logic_solved_cells.clear()
        self.needs_final_render = False

        target_value = max(1, int(self.target_number))

        bits_needed = 1
        while ((1 << bits_needed) - 1) * ((1 << bits_needed) - 1) < target_value:
            bits_needed += 1
        result_bits = max(1, target_value.bit_length())

        spacing = 5
        input_a_x = 10
        input_b_y = 10
        input_a_y0 = 15
        input_b_x0 = 15

        input_a = [(input_a_x, input_a_y0 + (i * spacing)) for i in range(bits_needed)]
        input_b = [(input_b_x0 + (i * spacing), input_b_y) for i in range(bits_needed)]
        gates = [(bx, ay) for _, ay in input_a for bx, _ in input_b]
        target_y = input_a_y0 + (bits_needed * spacing) + 10
        target = [(input_a_x + (i * spacing), target_y) for i in range(result_bits)]
        target_bits_le = [((target_value >> i) & 1) for i in range(result_bits)]

        def _place(coord: Coord, role: str, p_bias: float, state: int, mutation_override: int | None = None) -> None:
            self.activate(coord)
            self.p_bias[coord] = max(0.0, min(1.0, float(p_bias)))
            self.state[coord] = 1 if int(state) != 0 else 0
            self.logic_role[coord] = role
            self.structural_cells.add(coord)
            mut = int(round(self.p_bias[coord] * 7.0)) if mutation_override is None else int(mutation_override)
            self.structural_mutation[coord] = max(0, min(7, mut))
            self.set_mutation_type(coord, self.structural_mutation[coord])
            self.set_energy(coord, self.max_energy(coord))

        for coord in input_a:
            _place(coord, role="input_a", p_bias=0.5, state=self.rng.randint(0, 1))

        for coord in input_b:
            _place(coord, role="input_b", p_bias=0.5, state=self.rng.randint(0, 1))

        for coord in gates:
            _place(coord, role="gate", p_bias=0.5, state=self.rng.randint(0, 1))

        target_bits_by_coord: dict[Coord, int] = {}
        for bit_index, coord in enumerate(sorted(target, key=lambda c: c[0], reverse=True)):
            bit = target_bits_le[bit_index] if bit_index < len(target_bits_le) else 0
            target_bits_by_coord[coord] = bit

        for coord in target:
            _place(coord, role="target", p_bias=1.0, state=target_bits_by_coord.get(coord, 0), mutation_override=7)

    def update_exploration_fields(self) -> None:
        """Update deterministic smell and path-memory fields each tick."""
        if self.smell_field:
            new_smell: dict[Coord, float] = {}
            for coord, value in self.smell_field.items():
                decayed = value * self.smell_decay
                if decayed < 0.01:
                    continue
                new_smell[coord] = max(new_smell.get(coord, 0.0), decayed)
                spread = decayed * self.smell_diffusion
                if spread < 0.01:
                    continue
                cx, cy = coord
                for dx, dy in MOORE_OFFSETS:
                    nc = (cx + dx, cy + dy)
                    if not self.is_within_bounds(nc):
                        continue
                    if spread > new_smell.get(nc, 0.0):
                        new_smell[nc] = spread
            self.smell_field = new_smell

        for coord in self.food_clusters:
            self.smell_field[coord] = max(self.smell_field.get(coord, 0.0), self.smell_food_source)
        for coord in self.outpost_anchors:
            self.smell_field[coord] = max(self.smell_field.get(coord, 0.0), self.smell_outpost_source)

        if self.path_memory:
            for coord in tuple(self.path_memory.keys()):
                decayed = self.path_memory[coord] * self.path_memory_decay
                if decayed < 0.01:
                    self.path_memory.pop(coord, None)
                else:
                    self.path_memory[coord] = decayed

        for coord in self.alive_coords:
            self.path_memory[coord] = self.path_memory.get(coord, 0.0) + self.path_memory_deposit

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
        return abs(x) <= self.current_radius and abs(y) <= self.current_radius

    def register_seed_anchor(self, origin: Coord) -> None:
        self.seed_anchors.add(origin)

    def register_outpost_anchor(self, origin: Coord) -> None:
        self.outpost_anchors.add(origin)
        self.seed_anchors.add(origin)
        self._lock_outpost_area(origin, radius=self.outpost_lock_radius)

    def _lock_outpost_area(self, origin: Coord, radius: int = 2) -> None:
        ox, oy = origin
        base_mutation = self.mutation_type(origin)
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if max(abs(dx), abs(dy)) > radius:
                    continue
                coord = (ox + dx, oy + dy)
                if not self.is_within_bounds(coord):
                    continue
                self.structural_cells.add(coord)
                self.structural_mutation.setdefault(coord, base_mutation)

    def remove_structural(self, coord: Coord) -> None:
        self.structural_cells.discard(coord)
        self.structural_mutation.pop(coord, None)
        self.overcrowded_structural_cells.discard(coord)
        self.structural_overcrowded_ticks.pop(coord, None)

    def is_food(self, coord: Coord) -> bool:
        return coord in self.food_clusters

    def consume_food(self, coord: Coord) -> bool:
        if coord not in self.food_clusters:
            return False
        self.food_clusters.discard(coord)
        self.register_outpost_anchor(coord)
        return True

    def award_food_energy(self, coord: Coord) -> None:
        self.structural_cells.add(coord)
        self.structural_mutation.setdefault(coord, self.mutation_type(coord))
        boosted = min(self.max_energy(coord), self.energy(coord) + self.food_energy_bonus)
        self.set_energy(coord, max(boosted, self.max_energy(coord)))

    def set_coherence_percent(self, coherence: float) -> None:
        value = max(0.0, min(100.0, float(coherence)))
        self.last_coherence_percent = value
        if value >= self.coherence_high_threshold:
            self.coherence_high_streak += 1
        else:
            self.coherence_high_streak = 0

        if value <= self.coherence_low_threshold:
            self.coherence_low_streak += 1
        else:
            self.coherence_low_streak = 0

    def adapt_radius_from_coherence(self) -> None:
        if self.coherence_high_streak >= self.coherence_expand_ticks:
            self.current_radius = min(self.max_radius, self.current_radius + self.radius_step)
            self.coherence_high_streak = 0

        if self.coherence_low_streak >= self.coherence_contract_ticks:
            self.current_radius = max(self.min_radius, self.current_radius - self.radius_step)
            self.coherence_low_streak = 0

    def maybe_spawn_food_clusters(self) -> None:
        if self.food_spawn_interval <= 0:
            return
        if self.tick <= 0 or self.tick % self.food_spawn_interval != 0:
            return

        clusters = self.rng.randint(self.food_cluster_min, self.food_cluster_max)
        min_dist = max(1.0, self.current_radius * self.food_min_distance_ratio)
        max_dist = float(self.current_radius)

        for _ in range(clusters):
            placed = False
            for _attempt in range(24):
                distance = self.rng.uniform(min_dist, max_dist)
                angle = self.rng.uniform(0.0, math.tau)
                x = int(round(math.cos(angle) * distance))
                y = int(round(math.sin(angle) * distance))
                coord = (x, y)
                if coord in self.cells or coord in self.food_clusters:
                    continue
                if not self.is_within_bounds(coord):
                    continue
                self.food_clusters.add(coord)
                placed = True
                break
            if not placed:
                continue

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
        self.structural_overcrowded_ticks.pop(coord, None)
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

