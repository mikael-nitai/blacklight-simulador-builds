"""Pure expiration planning, independent of characters and mutable combat state.

Each effect has its own identity; effects of the same kind may coexist. A rule
can specify alternative deadlines (for example the source's next turn or a
round limit). This module decides only timing, never a power's legal effects.
"""

from dataclasses import dataclass
from enum import Enum


class Boundary(str, Enum):
    TURN_START = 'turn_start'
    TURN_END = 'turn_end'
    ROUND_START = 'round_start'
    ROUND_END = 'round_end'


@dataclass(frozen=True)
class TimePoint:
    boundary: Boundary
    occurrence: int
    actor: int | None = None

    def __post_init__(self) -> None:
        is_turn = self.boundary in (Boundary.TURN_START, Boundary.TURN_END)
        if (not isinstance(self.boundary, Boundary)
                or type(self.occurrence) is not int
                or self.occurrence < (1 if is_turn else 0)):
            raise ValueError('Invalid timing boundary or occurrence')
        if ((is_turn and (type(self.actor) is not int or self.actor < 0))
                or (not is_turn and self.actor is not None)):
            raise ValueError('Turn boundaries require an actor; round boundaries have none')

    def reaches(self, deadline: 'TimePoint') -> bool:
        return (self.boundary == deadline.boundary and self.actor == deadline.actor
                and self.occurrence >= deadline.occurrence)


@dataclass(frozen=True)
class TimedEffect:
    token: str
    kind: str
    subject: int
    source: int | None
    deadlines: tuple[TimePoint, ...]
    rules: tuple[str, ...]

    def __post_init__(self) -> None:
        if (any(not isinstance(value, str) or not value.strip()
                for value in (self.token, self.kind))
                or type(self.subject) is not int or self.subject < 0
                or self.source is not None and (type(self.source) is not int or self.source < 0)
                or not isinstance(self.deadlines, tuple)
                or any(not isinstance(point, TimePoint) for point in self.deadlines)
                or len(set(self.deadlines)) != len(self.deadlines)
                or not isinstance(self.rules, tuple) or not self.rules
                or any(not isinstance(rule, str) or not rule.strip() for rule in self.rules)):
            raise ValueError('Invalid timed effect definition')


@dataclass(frozen=True)
class ExpirationPlan:
    expired: tuple[TimedEffect, ...]
    remaining: tuple[TimedEffect, ...]


def expiration_plan(effects: tuple[TimedEffect, ...], now: TimePoint) -> ExpirationPlan:
    """Validate the whole input, then partition without mutation or reordering."""
    if (not isinstance(now, TimePoint) or not isinstance(effects, tuple)
            or any(not isinstance(effect, TimedEffect) for effect in effects)
            or len({effect.token for effect in effects}) != len(effects)):
        raise ValueError('Expiration planning requires distinct immutable effect instances')
    expired, remaining = [], []
    for effect in effects:
        target = expired if any(now.reaches(point) for point in effect.deadlines) else remaining
        target.append(effect)
    return ExpirationPlan(tuple(expired), tuple(remaining))
