from non_matrix.cell import Cell


def test_cell_alive_bit_helpers() -> None:
    cell = Cell(1, 2)
    assert cell.is_alive() is False

    cell.set_alive(True, tick=3)
    assert cell.is_alive() is True
    assert cell.last_touched_tick == 3

    cell.set_alive(False, tick=4)
    assert cell.is_alive() is False
    assert cell.last_touched_tick == 4


def test_cell_set_bits() -> None:
    cell = Cell(0, 0)
    cell.set_bits(0b1011, tick=9)
    assert cell.value == 0b1011
    assert cell.is_alive() is True
    assert cell.last_touched_tick == 9


def test_cell_mutation_type_bits_roundtrip() -> None:
    cell = Cell(0, 0)
    cell.set_mutation_type(5, tick=2)
    assert cell.mutation_type() == 5
    assert cell.last_touched_tick == 2

    cell.set_alive(True)
    assert cell.is_alive() is True
    assert cell.mutation_type() == 5


def test_cell_energy_roundtrip_and_decay() -> None:
    cell = Cell(0, 0)
    cell.set_energy(7, tick=1)
    assert cell.energy() == 7
    assert cell.last_touched_tick == 1

    remaining = cell.decay_energy(tick=2)
    assert remaining == 6
    assert cell.energy() == 6
    assert cell.last_touched_tick == 2

