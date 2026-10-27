"""Immutable battlefield inputs; unsupported terrain is never inferred."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CorridorMap:
    length: int
    initial_positions: tuple[int, int] = (0, 8)

    def __post_init__(self) -> None:
        if (type(self.length) is not int or self.length < 1
                or not isinstance(self.initial_positions, tuple) or len(self.initial_positions) != 2
                or any(type(value) is not int for value in self.initial_positions)):
            raise ValueError('A corridor needs integer length and two integer positions')
        left, right = self.initial_positions
        if not 0 <= left < right <= self.length:
            raise ValueError('Characters must start in distinct ordered cells inside the corridor')

    @property
    def distance(self) -> int:
        return self.initial_positions[1] - self.initial_positions[0]

    def record(self) -> dict:
        return {'kind': 'corridor', 'length': self.length,
                'initial_positions': list(self.initial_positions)}
