from __future__ import annotations

from dataclasses import dataclass

Coord = tuple[int, int]
ALIVE_MASK = 0b0001
MUTATION_MASK = 0b1110
ENERGY_SHIFT = 4
ENERGY_MASK = 0b1111 << ENERGY_SHIFT
MAX_ENERGY = 15


@dataclass(slots=True)
class Cell:
    """Sparse-grid cell with bitfield-ready integer state."""

    x: int
    y: int
    value: int = 0
    parent: Coord | None = None
    last_touched_tick: int = 0

    @property
    def coord(self) -> Coord:
        return (self.x, self.y)

    def is_alive(self) -> bool:
        return (self.value & ALIVE_MASK) == ALIVE_MASK

    def mutation_type(self) -> int:
        return (self.value & MUTATION_MASK) >> 1

    def set_mutation_type(self, mutation_index: int, tick: int | None = None) -> None:
        mutation_bits = (int(mutation_index) & 0b111) << 1
        self.value = (self.value & ~MUTATION_MASK) | mutation_bits
        if tick is not None:
            self.last_touched_tick = tick

    def energy(self) -> int:
        return (self.value & ENERGY_MASK) >> ENERGY_SHIFT

    def set_energy(self, amount: int, tick: int | None = None) -> None:
        bounded = max(0, min(MAX_ENERGY, int(amount)))
        energy_bits = bounded << ENERGY_SHIFT
        self.value = (self.value & ~ENERGY_MASK) | energy_bits
        if tick is not None:
            self.last_touched_tick = tick

    def decay_energy(self, tick: int | None = None) -> int:
        remaining = max(0, self.energy() - 1)
        self.set_energy(remaining, tick=tick)
        return remaining

    def drain_energy(self, cost: int, tick: int | None = None) -> int:
        remaining = max(0, self.energy() - max(0, int(cost)))
        self.set_energy(remaining, tick=tick)
        return remaining

    def set_alive(self, flag: bool, tick: int | None = None) -> None:
        if flag:
            self.value |= ALIVE_MASK
        else:
            self.value &= ~ALIVE_MASK
        if tick is not None:
            self.last_touched_tick = tick

    def set_bits(self, mask: int, tick: int | None = None) -> None:
        self.value = int(mask)
        if tick is not None:
            self.last_touched_tick = tick

