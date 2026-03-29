from non_matrix.sparse_grid import SparseGrid


def test_ensure_and_activate_and_prune() -> None:
    grid = SparseGrid()
    coord = grid.ensure((2, 3))
    assert coord == (2, 3)
    assert (2, 3) in grid.cells

    grid.activate((2, 3))
    assert (2, 3) in grid.alive_coords

    grid.deactivate((2, 3))
    assert (2, 3) not in grid.alive_coords
    assert (2, 3) not in grid.cells


def test_alive_neighbors_and_frontier() -> None:
    grid = SparseGrid()
    grid.activate((0, 0))
    grid.activate((1, 0))
    grid.activate((0, 1))

    assert grid.alive_neighbors((1, 1)) == 3

    frontier = grid.candidate_frontier()
    assert (2, 1) in frontier
    assert (-1, -1) in frontier


def test_newborn_inherits_parent_mutation_type_without_random_flip() -> None:
    grid = SparseGrid(mutation_chance=0.0)
    parent = grid.activate((0, 0))
    grid.set_mutation_type(parent, 6)

    child = grid.activate((1, 0), parent=(0, 0))
    assert grid.mutation_type(child) == 6


def test_newborn_mutation_can_flip_with_forced_chance() -> None:
    grid = SparseGrid(mutation_chance=1.0)
    parent = grid.activate((0, 0))
    grid.set_mutation_type(parent, 3)

    child = grid.activate((1, 0), parent=(0, 0))
    assert grid.mutation_type(child) != 3
    assert 0 <= grid.mutation_type(child) <= 7


def test_cull_to_max_active_removes_oldest_first() -> None:
    grid = SparseGrid(max_active_cells=2)
    a = grid.activate((0, 0))
    grid.touch(a)
    grid.meta[a].last_touched_tick = 1
    b = grid.activate((1, 0))
    grid.touch(b)
    grid.meta[b].last_touched_tick = 2
    c = grid.activate((2, 0))
    grid.touch(c)
    grid.meta[c].last_touched_tick = 3

    grid.cull_to_max_active()
    assert len(grid.alive_coords) == 2
    assert (0, 0) not in grid.alive_coords


def test_metadata_compaction_for_static_cells() -> None:
    grid = SparseGrid()
    coord = grid.activate((0, 0))
    grid.set_mutation_type(coord, 4)
    grid.set_energy(coord, 7)
    grid.static_ticks[coord] = 6
    grid.active_cells.discard(coord)

    grid.maybe_compact_static_metadata()
    assert coord not in grid.meta


def test_structural_cell_promoted_after_cumulative_occupancy() -> None:
    grid = SparseGrid()
    coord = grid.activate((0, 0))
    for _ in range(250):
        grid.record_occupancy_tick(coord)

    assert grid.is_structural(coord) is True
    assert grid.max_energy(coord) > 15


def test_growth_vector_inherits_from_parent_or_step_direction() -> None:
    grid = SparseGrid(mutation_chance=0.0)
    parent = grid.activate((0, 0))
    grid.set_growth_vector(parent, (1, 0))

    child = grid.activate((1, 0), parent=parent)
    assert grid.growth_vector(child) == (1, 0)

    root = grid.activate((10, 10))
    child2 = grid.activate((11, 11), parent=root)
    assert grid.growth_vector(child2) == (1, 1)


def test_dynamic_radius_bounds_check_uses_current_radius() -> None:
    grid = SparseGrid(min_radius=300, max_radius=1200)
    grid.current_radius = 300
    assert grid.is_within_bounds((300, 0)) is True
    assert grid.is_within_bounds((301, 0)) is False


def test_radius_expands_and_contracts_from_coherence_streaks() -> None:
    grid = SparseGrid(min_radius=300, max_radius=1200)
    grid.current_radius = 500

    for _ in range(10):
        grid.set_coherence_percent(75.0)
        grid.adapt_radius_from_coherence()
    assert grid.current_radius == 550

    for _ in range(20):
        grid.set_coherence_percent(30.0)
        grid.adapt_radius_from_coherence()
    assert grid.current_radius == 500


def test_food_clusters_spawn_far_from_center() -> None:
    grid = SparseGrid(min_radius=300, max_radius=1200)
    grid.current_radius = 600
    grid.tick = 150

    grid.maybe_spawn_food_clusters()
    assert 3 <= len(grid.food_clusters) <= 6
    min_dist = grid.current_radius * grid.food_min_distance_ratio
    for x, y in grid.food_clusters:
        assert (x * x + y * y) ** 0.5 >= (min_dist - 2.0)


def test_register_outpost_anchor_locks_local_structural_area() -> None:
    grid = SparseGrid(min_radius=300, max_radius=1200)
    center = (50, 50)
    grid.register_outpost_anchor(center)

    assert center in grid.outpost_anchors
    for dx in range(-grid.outpost_lock_radius, grid.outpost_lock_radius + 1):
        for dy in range(-grid.outpost_lock_radius, grid.outpost_lock_radius + 1):
            if max(abs(dx), abs(dy)) > grid.outpost_lock_radius:
                continue
            assert (center[0] + dx, center[1] + dy) in grid.structural_cells

