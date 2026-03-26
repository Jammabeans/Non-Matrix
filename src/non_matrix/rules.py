from __future__ import annotations

from collections import Counter
from collections.abc import Callable

from .cell import Coord
from .sparse_grid import MAX_CELLS, MOORE_OFFSETS, SparseGrid


RuleFn = Callable[[int, int], int]


def _rule_and_life(current_alive: int, neighbors: int) -> int:
    n2 = 1 if neighbors == 2 else 0
    n3 = 1 if neighbors == 3 else 0
    return (current_alive & n2) | n3


def _rule_xor(current_alive: int, neighbors: int) -> int:
    parity = neighbors & 1
    return current_alive ^ parity


def _rule_majority(current_alive: int, neighbors: int) -> int:
    return 1 if neighbors >= 4 else 0


def _rule_or(current_alive: int, neighbors: int) -> int:
    n3 = 1 if neighbors == 3 else 0
    return current_alive | n3


def _rule_xnor(current_alive: int, neighbors: int) -> int:
    parity = neighbors & 1
    return 1 if (current_alive ^ parity) == 0 else 0


def _rule_nand(current_alive: int, neighbors: int) -> int:
    crowded = 1 if neighbors > 3 else 0
    return 1 - (current_alive & crowded)


def _rule_shift_gate(current_alive: int, neighbors: int) -> int:
    shifted = (neighbors >> 1) & 1
    return current_alive & shifted


def _rule_birth_band(current_alive: int, neighbors: int) -> int:
    in_band = 1 if 2 <= neighbors <= 5 else 0
    return (current_alive | (1 - current_alive)) & in_band


MUTATION_RULES: dict[int, RuleFn] = {
    0: _rule_and_life,
    1: _rule_xor,
    2: _rule_majority,
    3: _rule_or,
    4: _rule_xnor,
    5: _rule_nand,
    6: _rule_shift_gate,
    7: _rule_birth_band,
}


def _alive_neighbor_coords(grid: SparseGrid, coord: Coord) -> list[Coord]:
    cx, cy = coord
    out: list[Coord] = []
    for dx, dy in MOORE_OFFSETS:
        neighbor = (cx + dx, cy + dy)
        if neighbor in grid.alive_coords:
            out.append(neighbor)
    return out


def _resolve_rule_type(grid: SparseGrid, coord: Coord, alive_neighbors: list[Coord]) -> int:
    if coord in grid.alive_coords:
        return grid.mutation_type(coord)

    if not alive_neighbors:
        return 0

    counts = Counter(grid.mutation_type(nc) for nc in alive_neighbors)
    if not counts:
        return 0
    return counts.most_common(1)[0][0]


def _select_parent_for_birth(grid: SparseGrid, alive_neighbors: list[Coord], rule_type: int) -> Coord | None:
    for nc in alive_neighbors:
        if grid.mutation_type(nc) == rule_type:
            return nc
    return alive_neighbors[0] if alive_neighbors else None


def _neighbor_counter(grid: SparseGrid, frontier: set[Coord]) -> dict[Coord, int]:
    counts: dict[Coord, int] = {}
    for coord in frontier:
        if coord not in grid.alive_coords:
            continue
        cx, cy = coord
        for dx, dy in MOORE_OFFSETS:
            nc = (cx + dx, cy + dy)
            counts[nc] = counts.get(nc, 0) + 1
    return counts


def step_life(grid: SparseGrid) -> None:
    """Advance one tick using local mutation-rule physics."""
    prior_active = max(1, len(grid.active_cells))
    candidates = grid.candidate_frontier()
    neighbor_counts = _neighbor_counter(grid, candidates)
    candidates |= set(neighbor_counts.keys())

    next_alive: set[Coord] = set()
    birth_parent: dict[Coord, Coord | None] = {}
    birth_force_inherit: dict[Coord, bool] = {}

    cooldown_strict = grid.cooldown_ticks > 0
    births_allowed = len(grid.cells) <= MAX_CELLS and not cooldown_strict

    for coord in candidates:
        neighbors = neighbor_counts.get(coord, 0)
        alive_neighbors = _alive_neighbor_coords(grid, coord) if neighbors > 0 else []
        alive = 1 if coord in grid.alive_coords else 0

        rule_type = _resolve_rule_type(grid, coord, alive_neighbors)
        rule_fn = MUTATION_RULES[rule_type]
        if cooldown_strict and alive == 1:
            survives = 1 if neighbors == 2 else 0
        else:
            survives = rule_fn(alive, neighbors)

        # Ghost-node bonus: structural dead coords are easier to reactivate.
        if alive == 0 and coord in grid.structural_cells and neighbors > 0 and survives == 0:
            if grid.rng.random() < 0.5:
                survives = 1

        if survives == 1:
            if alive == 0 and not births_allowed:
                continue
            next_alive.add(coord)
            if alive == 0:
                parent = _select_parent_for_birth(grid, alive_neighbors, rule_type)
                birth_parent[coord] = parent
                birth_force_inherit[coord] = bool(parent is not None and grid.is_old_growth(parent))

    # Selection pressure: crowding suffocation for currently alive cells.
    for coord in tuple(next_alive):
        if grid.is_anchor_protected(coord):
            continue
        if coord in grid.alive_coords and neighbor_counts.get(coord, 0) > 4:
            next_alive.discard(coord)

    # Root anchor persistence: alive cells near seed anchors cannot die.
    for coord in tuple(grid.alive_coords):
        if grid.is_anchor_protected(coord):
            next_alive.add(coord)

    # Spatial culling to keep roots inside bounded memory space.
    for coord in tuple(next_alive):
        if not grid.is_within_bounds(coord):
            next_alive.discard(coord)

    current_alive = set(grid.alive_coords)
    to_activate = next_alive - current_alive
    to_deactivate = current_alive - next_alive

    grid.tick += 1
    for coord in to_activate:
        grid.activate(
            coord,
            parent=birth_parent.get(coord),
            force_inherit=birth_force_inherit.get(coord, False),
        )
    for coord in to_deactivate:
        if grid.is_anchor_protected(coord) and grid.is_within_bounds(coord):
            continue
        grid.mark_for_death(coord)

    # Static culling from thinker frontier.
    for coord in tuple(grid.alive_coords):
        if coord in to_activate or coord in to_deactivate:
            grid.static_ticks[coord] = 0
            continue
        prev = grid.static_ticks.get(coord, 0) + 1
        grid.static_ticks[coord] = prev
        if prev >= 5:
            grid.active_cells.discard(coord)

    # Selection pressure + persistence balance: interaction reward and energy costs.
    total_cells = len(grid.cells)
    energy_tax = 1 + (total_cells // 5000)
    if grid.coherence_match:
        energy_tax = max(1, int(energy_tax * 0.5))

    if grid.pending_heat_dump:
        for coord in tuple(grid.alive_coords):
            grid.set_energy(coord, grid.energy(coord) // 2)
        grid.pending_heat_dump = False

    for coord in tuple(grid.alive_coords):
        grid.ensure_awake_metadata(coord)
        neighbors_count = neighbor_counts.get(coord, 0)
        neighbors = _alive_neighbor_coords(grid, coord) if neighbors_count > 0 else []
        if neighbors_count == 0:
            iso = grid.isolated_ticks(coord) + 1
            grid.set_isolated_ticks(coord, iso)
            if iso > 10 and not grid.is_anchor_protected(coord):
                grid.mark_for_death(coord)
                continue
        else:
            grid.set_isolated_ticks(coord, 0)

        if grid.is_anchor_protected(coord):
            grid.set_energy(coord, grid.max_energy(coord))
            continue

        # Metabolic reset for diversity interaction.
        if any(
            grid.mutation_type(nc) != grid.mutation_type(coord)
            for nc in neighbors
        ):
            grid.set_energy(coord, grid.max_energy(coord))
            continue

        # Global metabolic tax + variable mutation costs.
        mutation_cost = 2 if grid.mutation_type(coord) == 1 else 1
        effective_tax = max(1, int(energy_tax * 0.2)) if grid.is_structural(coord) else energy_tax
        drain_cost = effective_tax + mutation_cost
        remaining = max(0, grid.energy(coord) - drain_cost)
        grid.set_energy(coord, remaining)
        if remaining <= 0:
            grid.mark_for_death(coord)

    # Hard cap active population to protect framerate.
    grid.cull_to_max_active()

    # Lazy cleanup to avoid long blocking deletion stalls.
    grid.process_pending_deaths(limit=500)

    # Neural trace age map (same-spot survival memory).
    for coord in tuple(grid.alive_coords):
        grid.record_occupancy_tick(coord)
        if coord in to_activate:
            grid.survival_ticks[coord] = 0
            continue
        if coord in grid.pending_death:
            continue
        grid.survival_ticks[coord] = grid.survival_ticks.get(coord, 0) + 1

    # Compact metadata for very static cells.
    grid.maybe_compact_static_metadata()

    # Heat circuit breaker.
    total_energy = sum(grid.energy(coord) for coord in grid.alive_coords)
    if total_energy > 50_000:
        grid.pending_heat_dump = True

    # Bloom throttle: if active frontier grows >20%, force one strict cool-down tick.
    new_active = max(1, len(grid.active_cells))
    if new_active > int(prior_active * 1.2):
        grid.cooldown_ticks = 1
    elif grid.cooldown_ticks > 0:
        grid.cooldown_ticks -= 1

