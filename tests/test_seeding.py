from non_matrix.seeding import seed_text_utf8
from non_matrix.sparse_grid import SparseGrid


def test_utf8_seed_is_deterministic() -> None:
    g1 = SparseGrid()
    g2 = SparseGrid()

    a1 = seed_text_utf8(g1, "Hi", origin=(3, 4))
    a2 = seed_text_utf8(g2, "Hi", origin=(3, 4))

    assert a1 == a2
    assert g1.alive_coords == g2.alive_coords


def test_utf8_seed_non_ascii_supported() -> None:
    grid = SparseGrid()
    activated = seed_text_utf8(grid, "hé", origin=(0, 0))
    assert len(activated) > 0
    assert len(grid.alive_coords) == len(activated)


def test_empty_seed_no_activation() -> None:
    grid = SparseGrid()
    activated = seed_text_utf8(grid, "", origin=(0, 0))
    assert activated == set()
    assert grid.alive_coords == set()

