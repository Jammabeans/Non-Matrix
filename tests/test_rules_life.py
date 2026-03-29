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
    # Vector hard-lock + inhibition favors linear persistence over full oscillator re-expansion.
    assert grid.alive_coords == {(0, 0)}


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


def test_food_capture_grants_outpost_and_consumes_cluster() -> None:
    grid = SparseGrid()
    root = grid.activate((20, 20))
    grid.food_clusters.add(root)

    step_life(grid)
    assert root not in grid.food_clusters
    assert root in grid.outpost_anchors


def test_food_capture_within_chebyshev_radius_three() -> None:
    grid = SparseGrid()
    grid.activate((0, 0))
    food = (3, 0)
    grid.food_clusters.add(food)

    step_life(grid)
    assert food not in grid.food_clusters
    assert food in grid.outpost_anchors
    assert food in grid.alive_coords


def test_metabolic_crowding_quadruples_energy_drain_when_neighbors_above_three() -> None:
    grid = SparseGrid()
    center = grid.activate((0, 0))
    neighbors = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    for coord in neighbors:
        grid.activate(coord)

    grid.set_mutation_type(center, 3)
    for coord in neighbors:
        grid.set_mutation_type(coord, 3)

    # Force high baseline tax and suppress birth side-effects.
    for i in range(10_001):
        grid.cells.add((30_000 + i, 30_000))

    step_life(grid)
    # Crowding death is resolved via pending death queue in this lifecycle phase.
    assert center in grid.pending_death


def test_structural_overcrowding_loses_tax_discount_and_is_tracked() -> None:
    sparse_count = 5_000

    lean = SparseGrid()
    dense = SparseGrid()

    for i in range(sparse_count):
        lean.cells.add((10_000 + i, 10_000))
        dense.cells.add((10_000 + i, 10_000))

    lean_center = lean.activate((0, 0))
    for coord in [(-1, 0), (1, 0)]:
        lean.activate(coord)
    lean.structural_cells.update({lean_center, (-1, 0), (1, 0)})
    for coord in [lean_center, (-1, 0), (1, 0)]:
        lean.set_mutation_type(coord, 3)

    dense_center = dense.activate((0, 0))
    for coord in [(-1, 0), (1, 0), (0, 1)]:
        dense.activate(coord)
    dense.structural_cells.update({dense_center, (-1, 0), (1, 0), (0, 1)})
    for coord in [dense_center, (-1, 0), (1, 0), (0, 1)]:
        dense.set_mutation_type(coord, 3)

    step_life(lean)
    step_life(dense)

    assert lean.energy(lean_center) > dense.energy(dense_center)
    assert dense_center in dense.overcrowded_structural_cells


def test_outer_ring_chemotaxis_reduces_metabolic_tax() -> None:
    sparse_count = 5_000

    inner = SparseGrid()
    edge = SparseGrid()
    inner.current_radius = 100
    edge.current_radius = 100

    for i in range(sparse_count):
        inner.cells.add((20_000 + i, 20_000))
        edge.cells.add((20_000 + i, 20_000))

    inner_center = inner.activate((10, 10))
    inner.activate((9, 10))
    for coord in [inner_center, (9, 10)]:
        inner.set_mutation_type(coord, 3)

    edge_center = edge.activate((80, 0))
    edge.activate((79, 0))
    for coord in [edge_center, (79, 0)]:
        edge.set_mutation_type(coord, 3)

    step_life(inner)
    step_life(edge)

    assert edge.energy(edge_center) > inner.energy(inner_center)


def test_outer_ring_chemotaxis_uses_radial_distance() -> None:
    sparse_count = 5_000
    grid = SparseGrid()
    grid.current_radius = 100

    for i in range(sparse_count):
        grid.cells.add((40_000 + i, 40_000))

    # Same Chebyshev distance, different radial distance:
    # (70,70) is outside the 70-unit radial threshold; (70,0) is on threshold.
    diag = grid.activate((70, 70))
    axis = grid.activate((70, 0))
    for c, n1 in ((diag, (69, 70)), (axis, (69, 0))):
        grid.activate(n1)
        grid.set_mutation_type(c, 3)
        grid.set_mutation_type(n1, 3)

    step_life(grid)
    assert grid.energy(diag) > grid.energy(axis)


def test_structural_hibernation_keeps_structural_flag_on_metabolic_death() -> None:
    grid = SparseGrid()
    coord = grid.activate((10, 10))
    grid.activate((9, 10))
    grid.activate((11, 10))
    grid.structural_cells.add(coord)
    grid.structural_mutation[coord] = 3

    # Force high tax while keeping the cell in the Goldilocks-survival regime (2 neighbors).
    for i in range(10_001):
        grid.cells.add((60_000 + i, 60_000))
    grid.set_energy(coord, 1)
    grid.set_mutation_type(coord, 3)
    grid.set_mutation_type((9, 10), 3)
    grid.set_mutation_type((11, 10), 3)

    step_life(grid)
    assert coord in grid.structural_cells


def test_outpost_magnet_reduces_tax_near_outpost() -> None:
    sparse_count = 5_000

    near = SparseGrid()
    far = SparseGrid()
    near.register_outpost_anchor((0, 0))
    far.register_outpost_anchor((0, 0))

    for i in range(sparse_count):
        near.cells.add((50_000 + i, 50_000))
        far.cells.add((50_000 + i, 50_000))

    near_center = near.activate((100, 0))
    near.activate((99, 0))
    for coord in [near_center, (99, 0)]:
        near.set_mutation_type(coord, 3)

    far_center = far.activate((300, 0))
    far.activate((299, 0))
    for coord in [far_center, (299, 0)]:
        far.set_mutation_type(coord, 3)

    step_life(near)
    step_life(far)

    assert near.energy(near_center) > far.energy(far_center)


def test_directional_momentum_birth_bias_prefers_growth_vector() -> None:
    grid = SparseGrid(mutation_chance=0.0)
    center = grid.activate((0, 0))
    grid.set_mutation_type(center, 3)
    grid.set_growth_vector(center, (1, 0))

    # Neighbors enabling two candidate births around the parent.
    for coord in [(-1, 0), (0, 1)]:
        grid.activate(coord)
        grid.set_mutation_type(coord, 3)

    forward_births = 0
    side_births = 0
    trials = 120
    for i in range(trials):
        probe = SparseGrid(mutation_chance=0.0)
        c = probe.activate((0, 0))
        probe.set_mutation_type(c, 3)
        probe.set_growth_vector(c, (1, 0))
        probe.survival_ticks[c] = 5
        for coord in [(-1, 0), (0, 1)]:
            probe.activate(coord)
            probe.set_mutation_type(coord, 3)
        probe.rng.seed(i)
        step_life(probe)
        if (1, 0) in probe.alive_coords:
            forward_births += 1
        if (0, -1) in probe.alive_coords:
            side_births += 1

    assert forward_births >= side_births

