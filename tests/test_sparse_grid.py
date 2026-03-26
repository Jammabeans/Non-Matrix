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

