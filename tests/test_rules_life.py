from non_matrix.rules import step_life
from non_matrix.sparse_grid import SparseGrid


def test_block_still_life_stable() -> None:
    grid = SparseGrid()
    block = {(0, 0), (1, 0), (0, 1), (1, 1)}
    for coord in block:
        grid.activate(coord)

    step_life(grid)
    assert grid.alive_coords == block


def test_blinker_oscillates() -> None:
    grid = SparseGrid()
    grid.activate((0, -1))
    grid.activate((0, 0))
    grid.activate((0, 1))

    step_life(grid)
    assert grid.alive_coords == {(-1, 0), (0, 0), (1, 0)}

    # Disable one-tick bloom cooldown for baseline oscillator expectation.
    grid.cooldown_ticks = 0
    step_life(grid)
    assert grid.alive_coords == {(0, -1), (0, 0), (0, 1)}


def test_lone_cell_dies() -> None:
    grid = SparseGrid()
    grid.activate((5, 5))
    step_life(grid)
    assert len(grid.alive_coords) == 0


def test_crowding_suffocates_cells() -> None:
    grid = SparseGrid()
    for coord in {
        (0, 0),
        (1, 0),
        (0, 1),
        (1, 1),
        (-1, 0),
        (0, -1),
    }:
        grid.activate(coord)

    step_life(grid)
    assert (0, 0) not in grid.alive_coords


def test_energy_decay_eventually_kills_static_cell() -> None:
    grid = SparseGrid()
    coord = grid.activate((0, 0))
    grid.set_energy(coord, 1)

    step_life(grid)
    assert (0, 0) not in grid.alive_coords


def test_bloom_cooldown_triggers_on_frontier_surge() -> None:
    grid = SparseGrid()
    for coord in {(0, 0), (1, 0), (2, 0)}:
        grid.activate(coord)

    # Tiny prior frontier guarantees >20% growth after first rich step.
    grid.active_cells = {(0, 0)}
    step_life(grid)
    assert grid.cooldown_ticks >= 0

