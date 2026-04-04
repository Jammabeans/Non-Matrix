from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable

from .cell import Coord
from .modes import SimMode
from .sparse_grid import MAX_CELLS, MOORE_OFFSETS, SparseGrid


RuleFn = Callable[[int, int], int]
BIRTH_SCORE_THRESHOLD = -0.25


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


def _deterministic_birth_score(
    grid: SparseGrid,
    coord: Coord,
    step_vec: Coord,
    parent_vec: Coord,
    neighbors: int,
) -> float:
    smell = grid.smell_field.get(coord, 0.0)
    memory_penalty = grid.path_memory.get(coord, 0.0)

    alignment = 0.0
    if parent_vec != (0, 0):
        sx, sy = step_vec
        px, py = parent_vec
        dot = (sx * px) + (sy * py)
        alignment = dot / 2.0

    crowding_penalty = float(max(0, neighbors - grid.mycelium_target_neighbors))
    return (
        (grid.score_smell_weight * smell)
        + (grid.score_alignment_weight * alignment)
        - (grid.score_memory_penalty_weight * memory_penalty)
        - (grid.score_crowding_penalty_weight * crowding_penalty)
    )


def _select_parent_for_birth_deterministic(
    grid: SparseGrid,
    coord: Coord,
    alive_neighbors: list[Coord],
    rule_type: int,
    neighbors: int,
) -> tuple[Coord | None, Coord, float]:
    if not alive_neighbors:
        return None, (0, 0), float("-inf")

    preferred = [nc for nc in alive_neighbors if grid.mutation_type(nc) == rule_type]
    candidates = preferred if preferred else alive_neighbors

    best: tuple[float, Coord, Coord] | None = None
    for parent in candidates:
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
        growth_vec = parent_vec if has_momentum else step_vec
        score = _deterministic_birth_score(
            grid=grid,
            coord=coord,
            step_vec=step_vec,
            parent_vec=parent_vec,
            neighbors=neighbors,
        )

        key = (score, -parent[0], -parent[1])
        if best is None or key > (best[0], -best[1][0], -best[1][1]):
            best = (score, parent, growth_vec)

    if best is None:
        return None, (0, 0), float("-inf")
    return best[1], best[2], best[0]


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


def _step_life_mycelium(grid: SparseGrid) -> None:
    """Advance one tick using local mutation-rule physics."""
    grid.update_exploration_fields()
    prior_active = max(1, len(grid.active_cells))
    candidates = grid.candidate_frontier()
    neighbor_counts = _neighbor_counter(grid, candidates)
    candidates |= set(neighbor_counts.keys())
    prior_alive_count = len(grid.alive_coords)
    cull_out_of_bounds_count = 0
    isolation_death_marks = 0
    energy_death_marks = 0
    bootstrap_ticks = max(0, int(getattr(grid, "mycelium_bootstrap_ticks", 0)))
    bootstrap_active = (
        grid.tick < bootstrap_ticks
        and bool(grid.seed_anchors)
        and not bool(grid.outpost_anchors)
    )
    bootstrap_crowding_bonus = (
        max(0, int(getattr(grid, "mycelium_bootstrap_crowding_bonus", 0))) if bootstrap_active else 0
    )
    bootstrap_energy_discount = (
        max(0.0, min(0.95, float(getattr(grid, "mycelium_bootstrap_energy_discount", 0.0))))
        if bootstrap_active
        else 0.0
    )
    effective_crowding_threshold = grid.crowding_threshold + bootstrap_crowding_bonus

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

        # Ghost-node deterministic bonus: reactivate structural dead coords when local score is favorable.
        if alive == 0 and coord in grid.structural_cells and neighbors > 0 and survives == 0:
            score = _deterministic_birth_score(
                grid=grid,
                coord=coord,
                step_vec=(0, 0),
                parent_vec=grid.growth_vector(coord),
                neighbors=neighbors,
            )
            if score >= 0.0:
                survives = 1

        if survives == 1:
            if alive == 0 and not births_allowed:
                continue
            if alive == 0:
                parent, growth_vec, score = _select_parent_for_birth_deterministic(
                    grid=grid,
                    coord=coord,
                    alive_neighbors=alive_neighbors,
                    rule_type=rule_type,
                    neighbors=neighbors,
                )
                if score < BIRTH_SCORE_THRESHOLD and coord not in grid.food_clusters:
                    continue
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
                    growth_vec = parent_vec if has_momentum else step_vec
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
        if coord in grid.alive_coords and neighbor_counts.get(coord, 0) > effective_crowding_threshold:
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
            cull_out_of_bounds_count += 1

    current_alive = set(grid.alive_coords)
    to_activate = next_alive - current_alive
    to_deactivate = current_alive - next_alive
    rule_deactivate_count = len(to_deactivate)

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
                isolation_death_marks += 1
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
        if neighbors_count > effective_crowding_threshold:
            drain_cost *= grid.crowding_multiplier
        if bootstrap_energy_discount > 0.0:
            drain_cost = max(0, int(round(float(drain_cost) * (1.0 - bootstrap_energy_discount))))
        remaining = max(0, grid.energy(coord) - drain_cost)
        grid.set_energy(coord, remaining)
        if remaining <= 0:
            grid.mark_for_death(coord)
            energy_death_marks += 1

    # Hard cap active population to protect framerate.
    cull_before = len(grid.cells)
    protected_before = sum(1 for coord in grid.cells if grid.is_anchor_protected(coord))
    grid.cull_to_max_active()
    cull_removed = max(0, cull_before - len(grid.cells))

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

    if (
        grid.debug_mycelium_diagnosis
        and grid.debug_mycelium_log_every > 0
        and (grid.tick % int(grid.debug_mycelium_log_every)) == 0
    ):
        anchor_survivors = sum(1 for coord in grid.alive_coords if grid.is_anchor_protected(coord))
        print(
            "[MYCELIUM_DIAG]"
            f" tick={grid.tick}"
            f" alive_before={prior_alive_count}"
            f" alive_after={len(grid.alive_coords)}"
            f" max_active={grid.max_active_cells}"
            f" cull_removed={cull_removed}"
            f" protected_before={protected_before}"
            f" anchor_survivors={anchor_survivors}"
            f" out_of_bounds_culled={cull_out_of_bounds_count}"
            f" radius={grid.current_radius}"
            f" anchors={len(grid.seed_anchors)}"
            f" to_activate={len(to_activate)}"
            f" to_deactivate={rule_deactivate_count}"
            f" overcrowding_deaths={len(overcrowding_deaths)}"
            f" isolation_marks={isolation_death_marks}"
            f" energy_marks={energy_death_marks}"
            f" pending_death={len(grid.pending_death)}"
            f" cooldown={grid.cooldown_ticks}"
            f" births_allowed={int(births_allowed)}"
            f" bootstrap={int(bootstrap_active)}"
            f" crowding_threshold={effective_crowding_threshold}"
            f" energy_discount={bootstrap_energy_discount:.2f}"
        )

    grid.maybe_spawn_food_clusters()


def _p_bias_to_mutation_type(p_bias: float) -> int:
    bounded = max(0.0, min(1.0, float(p_bias)))
    return int(round(bounded * 7.0))


def _step_life_logic_factorizer(grid: SparseGrid) -> None:
    """Full-adder pressure stepping for multiplication matrix mode."""
    grid.tick += 1
    prev_state = dict(grid.state)

    if grid.logic_solved:
        grid.logic_pause_requested = True
        return

    grid.logic_pause_requested = False

    input_a = sorted((coord for coord, role in grid.logic_role.items() if role == "input_a"), key=lambda c: c[1])
    input_b = sorted((coord for coord, role in grid.logic_role.items() if role == "input_b"), key=lambda c: c[0])
    input_a_bits = sorted(input_a, key=lambda c: c[1], reverse=True)  # little-endian: bottom bit = 1
    input_b_bits = sorted(input_b, key=lambda c: c[0], reverse=True)  # little-endian: right bit = 1
    target = sorted((coord for coord, role in grid.logic_role.items() if role == "target"), key=lambda c: c[0])
    target_set = set(target)
    hot_flip = max(0.0, min(1.0, float(grid.logic_flip_hot_chance)))
    cold_flip = max(0.0, min(1.0, float(grid.logic_flip_cold_chance)))
    gate_hot = max(0.0, min(1.0, float(grid.logic_gate_hot_chance)))
    gate_cold = max(0.0, min(1.0, float(grid.logic_gate_cold_chance)))

    pressure: dict[Coord, float] = {coord: 0.0 for coord in grid.state.keys()}
    flip_prob: dict[Coord, float] = {coord: 0.05 for coord in grid.state.keys()}

    def _set_hot(coord: Coord, strength: float = 0.95) -> None:
        flip_prob[coord] = max(flip_prob.get(coord, 0.0), max(0.0, min(0.95, strength)))

    def _set_cold(coord: Coord, strength: float = 0.005) -> None:
        if flip_prob.get(coord, 0.0) < 0.95:
            flip_prob[coord] = min(flip_prob.get(coord, 1.0), max(0.0, strength))
    column_match_flags: list[bool] = []
    carry_in = 0

    gate_cols = sorted({coord[0] for coord, role in grid.logic_role.items() if role == "gate"})
    target_sorted_le = sorted(target, key=lambda c: c[0], reverse=True)
    target_bits_le = [1 if int(grid.state.get(coord, 0)) != 0 else 0 for coord in target_sorted_le]
    target_value = sum((bit << i) for i, bit in enumerate(target_bits_le))
    target_bits_by_coord = {coord: bit for coord, bit in zip(target_sorted_le, target_bits_le, strict=False)}
    all_gate_coords = [coord for coord, role in grid.logic_role.items() if role == "gate"]

    column_output_bits: list[int] = []
    column_match_by_x: dict[int, bool] = {}

    # Full-adder style from right (LSB side) to left, with carry propagation across gate columns.
    for col_index, gx in enumerate(reversed(gate_cols)):
        gate_col = [coord for coord, role in grid.logic_role.items() if role == "gate" and coord[0] == gx]
        active = sum(1 for coord in gate_col if int(grid.state.get(coord, 0)) != 0)
        column_sum = active + carry_in
        sum_bit = column_sum & 1
        carry_out = column_sum >> 1

        target_bit = target_bits_le[col_index] if col_index < len(target_bits_le) else 0
        match = sum_bit == target_bit
        column_match_flags.append(match)
        column_output_bits.append(sum_bit)
        column_match_by_x[gx] = match

        if not match:
            # Massive pressure to all participants of the failing column.
            for a_coord in input_a:
                pressure[a_coord] = pressure.get(a_coord, 0.0) + 2.0
                _set_hot(a_coord, hot_flip)
                if grid.rng.random() < 0.90:
                    cur = 1 if int(grid.state.get(a_coord, 0)) != 0 else 0
                    grid.p_bias[a_coord] = 0.9 if cur == 0 else 0.1
            b_coord = next((coord for coord in input_b if coord[0] == gx), None)
            if b_coord is not None:
                pressure[b_coord] = pressure.get(b_coord, 0.0) + 2.0
                _set_hot(b_coord, hot_flip)
                if grid.rng.random() < 0.90:
                    cur = 1 if int(grid.state.get(b_coord, 0)) != 0 else 0
                    grid.p_bias[b_coord] = 0.9 if cur == 0 else 0.1
            for g_coord in gate_col:
                pressure[g_coord] = pressure.get(g_coord, 0.0) + 1.0
                _set_hot(g_coord, gate_hot)
        else:
            for a_coord in input_a:
                _set_cold(a_coord, min(cold_flip, 0.0001))
                cur = 1 if int(grid.state.get(a_coord, 0)) != 0 else 0
                grid.p_bias[a_coord] = 0.9999 if cur == 1 else 0.0001
            b_coord = next((coord for coord in input_b if coord[0] == gx), None)
            if b_coord is not None:
                _set_cold(b_coord, min(cold_flip, 0.0001))
                cur = 1 if int(grid.state.get(b_coord, 0)) != 0 else 0
                grid.p_bias[b_coord] = 0.9999 if cur == 1 else 0.0001
            for g_coord in gate_col:
                _set_cold(g_coord, gate_cold)

        carry_in = carry_out

    # Extend carry chain to match 6-bit (or dynamic) target width.
    while len(column_output_bits) < len(target_bits_le):
        column_output_bits.append(carry_in & 1)
        carry_in >>= 1

    for bit_index in range(len(target_bits_le)):
        out_bit = column_output_bits[bit_index] if bit_index < len(column_output_bits) else 0
        bit_match = out_bit == target_bits_le[bit_index]
        column_match_flags.append(bit_match)
        if bit_index < len(gate_cols):
            gx = list(reversed(gate_cols))[bit_index]
            column_match_by_x[gx] = column_match_by_x.get(gx, True) and bit_match
        if not bit_match:
            for a_coord in input_a:
                pressure[a_coord] = pressure.get(a_coord, 0.0) + 2.0
                _set_hot(a_coord, hot_flip)
            for b_coord in input_b:
                pressure[b_coord] = pressure.get(b_coord, 0.0) + 2.0
                _set_hot(b_coord, hot_flip)
            for g_coord in all_gate_coords:
                pressure[g_coord] = pressure.get(g_coord, 0.0) + 1.0
                _set_hot(g_coord, gate_hot)

    # Cross-talk: each gate directly pressures its row (A_i) and column (B_j).
    for a_coord in input_a:
        for b_coord in input_b:
            gate_coord = (b_coord[0], a_coord[1])
            if grid.logic_role.get(gate_coord) != "gate":
                continue
            a_state = 1 if int(grid.state.get(a_coord, 0)) != 0 else 0
            b_state = 1 if int(grid.state.get(b_coord, 0)) != 0 else 0
            expected_gate = a_state & b_state
            gate_state = 1 if int(grid.state.get(gate_coord, 0)) != 0 else 0
            if gate_state != expected_gate:
                pressure[a_coord] = pressure.get(a_coord, 0.0) + 1.5
                pressure[b_coord] = pressure.get(b_coord, 0.0) + 1.5
                pressure[gate_coord] = pressure.get(gate_coord, 0.0) + 1.5
                _set_hot(a_coord, hot_flip)
                _set_hot(b_coord, hot_flip)
                _set_hot(gate_coord, gate_hot)
            else:
                _set_cold(gate_coord, gate_cold)

    all_match = bool(column_match_flags) and all(column_match_flags)
    a_value = sum((1 << i) for i, coord in enumerate(input_a_bits) if int(grid.state.get(coord, 0)) != 0)
    b_value = sum((1 << i) for i, coord in enumerate(input_b_bits) if int(grid.state.get(coord, 0)) != 0)
    current_guess = a_value * b_value
    total_error = abs(target_value - current_guess)
    denom = max(1.0, float(target_value))
    global_temp = max(0.0, min(1.0, total_error / denom))
    solved_math = (a_value * b_value) == target_value
    if total_error == 0:
        grid.logic_success_streak += 1
    else:
        grid.logic_success_streak = 0

    if grid.logic_success_streak >= max(1, int(grid.logic_success_streak_ticks)):
        grid.logic_solved = True
        grid.logic_pause_requested = True
        grid.needs_final_render = True
        grid.logic_solved_cells.clear()
        for coord, role in grid.logic_role.items():
            if role in {"input_a", "input_b", "gate", "target"}:
                grid.logic_solved_cells.add((coord[0], coord[1]))
            if role in {"input_a", "input_b"}:
                bit = 1 if int(grid.state.get(coord, 0)) != 0 else 0
                grid.p_bias[coord] = 1.0 if bit == 1 else 0.0
                grid.set_mutation_type(coord, _p_bias_to_mutation_type(grid.p_bias[coord]))
                grid.touch(coord)

    jolt_active = False
    if (
        grid.logic_stagnation_ticks > max(1, int(grid.logic_jolt_threshold_ticks))
        and not grid.logic_solved
        and total_error > 0
    ):
        jolt_active = True
        grid.logic_resume_requested = True
        grid.logic_pause_requested = False
        for coord, role in grid.logic_role.items():
            if role != "target":
                grid.p_bias[coord] = max(0.0, min(1.0, float(grid.logic_jolt_bias)))
        grid.logic_jolt_notice_ticks = 18

    # Keep target anchors clamped to binary 1111 and M7 visual coding.
    for coord in target_set:
        grid.p_bias[coord] = 1.0
        grid.state[coord] = 1 if target_bits_by_coord.get(coord, 0) != 0 else 0
        grid.set_mutation_type(coord, 7)
        grid.touch(coord)

    for coord in tuple(grid.state.keys()):
        if coord not in grid.cells:
            continue

        role = grid.logic_role.get(coord, "gate")
        if coord in target_set or role == "target":
            continue

        prev_bias = max(0.0, min(1.0, float(grid.p_bias.get(coord, 0.5))))
        # Exponential pressure response for sharper search dynamics.
        next_bias = 1.0 - ((1.0 - prev_bias) * math.exp(-max(0.0, pressure.get(coord, 0.0))))
        next_bias = max(0.0, min(1.0, next_bias))
        grid.p_bias[coord] = next_bias

        flip_chance = max(0.0, min(0.95, flip_prob.get(coord, 0.0)))
        flip_chance = max(flip_chance, global_temp * 0.9)
        if total_error == 0:
            flip_chance = 0.0
        if jolt_active:
            flip_chance = max(flip_chance, 0.8)
        if grid.rng.random() < flip_chance:
            current = 1 if int(grid.state.get(coord, 0)) != 0 else 0
            grid.state[coord] = 0 if current == 1 else 1

        grid.set_mutation_type(coord, _p_bias_to_mutation_type(next_bias))
        grid.touch(coord)

    if total_error == 0:
        grid.logic_stagnation_ticks = 0
        grid.logic_jolt_notice_ticks = 0
    elif grid.state == prev_state:
        grid.logic_stagnation_ticks += 1
    else:
        grid.logic_stagnation_ticks = 0

    if grid.logic_jolt_notice_ticks > 0:
        grid.logic_jolt_notice_ticks -= 1


def step_life(grid: SparseGrid) -> None:
    if grid.mode == SimMode.MYCELIUM:
        _step_life_mycelium(grid)
    else:
        _step_life_logic_factorizer(grid)

