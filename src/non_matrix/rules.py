from __future__ import annotations

import math
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


def _within_45_cone(step_vec: Coord, forward_vec: Coord) -> bool:
    return _within_cone(step_vec, forward_vec, cone_degrees=45.0)


def _within_cone(step_vec: Coord, forward_vec: Coord, cone_degrees: float) -> bool:
    sx, sy = step_vec
    fx, fy = forward_vec
    if (sx, sy) == (0, 0) or (fx, fy) == (0, 0):
        return True
    dot = (sx * fx) + (sy * fy)
    if dot <= 0:
        return False
    step_norm_sq = (sx * sx) + (sy * sy)
    fwd_norm_sq = (fx * fx) + (fy * fy)
    cos_threshold = math.cos(math.radians(max(0.0, min(180.0, cone_degrees))))
    return (dot * dot) >= (step_norm_sq * fwd_norm_sq * (cos_threshold * cos_threshold))


def step_life(grid: SparseGrid) -> None:
    """Advance one tick using local mutation-rule physics."""
    prior_active = max(1, len(grid.active_cells))
    candidates = grid.candidate_frontier()
    neighbor_counts = _neighbor_counter(grid, candidates)
    candidates |= set(neighbor_counts.keys())

    next_alive: set[Coord] = set()
    birth_parent: dict[Coord, Coord | None] = {}
    birth_force_inherit: dict[Coord, bool] = {}
    birth_growth_vector: dict[Coord, Coord] = {}
    overcrowding_deaths: set[Coord] = set()

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
            if alive == 0:
                parent = _select_parent_for_birth(grid, alive_neighbors, rule_type)
                if parent is not None:
                    px, py = parent
                    dx = 0 if coord[0] == px else (1 if coord[0] > px else -1)
                    dy = 0 if coord[1] == py else (1 if coord[1] > py else -1)
                    step_vec = (dx, dy)
                    parent_vec = grid.growth_vector(parent)
                    if parent_vec != (0, 0) and not _within_cone(step_vec, parent_vec, grid.vector_cone_degrees):
                        continue

                    parent_structural_neighbors = 0
                    if grid.lateral_inhibition_enabled and grid.is_structural(parent):
                        parent_structural_neighbors = sum(
                            1 for nc in _alive_neighbor_coords(grid, parent) if grid.is_structural(nc)
                        )
                    if parent_vec != (0, 0) and parent_structural_neighbors == grid.mycelium_target_neighbors:
                        opposite = (-parent_vec[0], -parent_vec[1])
                        if step_vec not in (parent_vec, opposite):
                            continue

                    has_momentum = (
                        grid.vector_bias_enabled
                        and parent_vec != (0, 0)
                        and grid.survival_ticks.get(parent, 0) >= grid.vector_bias_maturity_ticks
                    )
                    if has_momentum:
                        directional_chance = (
                            grid.vector_bias_forward_chance
                            if step_vec == parent_vec
                            else grid.vector_bias_side_chance
                        )
                        if grid.rng.random() > directional_chance:
                            continue
                        growth_vec = parent_vec
                    else:
                        growth_vec = step_vec
                else:
                    growth_vec = (0, 0)

                next_alive.add(coord)
                birth_parent[coord] = parent
                birth_force_inherit[coord] = bool(parent is not None and grid.is_old_growth(parent))
                birth_growth_vector[coord] = growth_vec
            else:
                next_alive.add(coord)

    # Selection pressure: crowding suffocation for currently alive cells.
    for coord in tuple(next_alive):
        if grid.is_anchor_protected(coord):
            continue
        if coord in grid.alive_coords and neighbor_counts.get(coord, 0) > grid.crowding_threshold:
            next_alive.discard(coord)
            overcrowding_deaths.add(coord)

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
            growth_vector=birth_growth_vector.get(coord),
        )
    for coord in to_deactivate:
        if grid.is_anchor_protected(coord) and grid.is_within_bounds(coord):
            continue
        grid.mark_for_death(coord)

    # Foraging capture radius: any live cell within Chebyshev distance <= 3 captures food.
    captured_food: dict[Coord, Coord] = {}
    for food in tuple(grid.food_clusters):
        fx, fy = food
        captor: Coord | None = None
        for cell in grid.alive_coords:
            if max(abs(cell[0] - fx), abs(cell[1] - fy)) <= grid.food_capture_radius:
                captor = cell
                break
        if captor is not None:
            captured_food[food] = captor

    for food, captor in captured_food.items():
        if grid.consume_food(food):
            grid.activate(food, parent=captor, force_inherit=True)
            grid.set_energy(food, grid.max_energy(food))
            grid.award_food_energy(captor)

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

    grid.overcrowded_structural_cells.clear()

    for coord in tuple(grid.alive_coords):
        grid.ensure_awake_metadata(coord)

        if coord in grid.pending_death:
            continue

        neighbors_count = neighbor_counts.get(coord, 0)
        neighbors = _alive_neighbor_coords(grid, coord) if neighbors_count > 0 else []
        structural_neighbors = sum(1 for nc in neighbors if grid.is_structural(nc))
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
        is_structural = grid.is_structural(coord)
        overcrowded_structural = is_structural and structural_neighbors > grid.structural_overcrowded_neighbors
        if overcrowded_structural:
            grid.overcrowded_structural_cells.add(coord)

        effective_tax = energy_tax
        if is_structural and not overcrowded_structural:
            effective_tax = max(1, int(energy_tax * grid.structural_discount_factor))

        if is_structural:
            if neighbors_count > grid.structural_hibernate_overcrowd_neighbors:
                over_ticks = grid.structural_overcrowded_ticks.get(coord, 0) + 1
                grid.structural_overcrowded_ticks[coord] = over_ticks
                if over_ticks > grid.structural_hibernate_ticks:
                    grid.remove_structural(coord)
                    is_structural = False
            else:
                grid.structural_overcrowded_ticks[coord] = 0

        # Outpost magnet: near established outposts, metabolic pressure collapses.
        if any(
            ((coord[0] - ox) * (coord[0] - ox) + (coord[1] - oy) * (coord[1] - oy)) <= (grid.outpost_magnet_radius * grid.outpost_magnet_radius)
            for ox, oy in grid.outpost_anchors
        ):
            effective_tax = max(1, int(effective_tax * grid.outpost_magnet_discount_factor))

        # Chemotaxis: lower metabolic pressure near the edge to pull growth outward.
        edge_band_start = grid.current_radius * grid.chemotaxis_outer_ratio
        edge_distance = math.hypot(coord[0], coord[1])
        if edge_distance > edge_band_start:
            effective_tax = max(1, int(effective_tax * grid.chemotaxis_discount_factor))

        # Goldilocks vine logic: exactly 2 neighbors is optimal.
        if grid.mycelium_zero_tax_enabled and neighbors_count == grid.mycelium_target_neighbors:
            effective_tax = 0
        vine_multiplier = 1 if neighbors_count == grid.mycelium_target_neighbors else grid.vine_off_target_multiplier
        drain_cost = (effective_tax + mutation_cost) * vine_multiplier
        if neighbors_count > grid.crowding_threshold:
            drain_cost *= grid.crowding_multiplier
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

    grid.maybe_spawn_food_clusters()

