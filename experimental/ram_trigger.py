"""Experimental one-dimensional Ram trigger; no attack or damage is resolved."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Approach:
    actor: str
    target: str
    turn: int
    action: str
    before: int
    after: int
    speed: int

    def __post_init__(self):
        if (not isinstance(self.actor, str) or not self.actor
                or not isinstance(self.target, str) or not self.target or self.actor == self.target
                or type(self.turn) is not int or self.turn < 1
                or self.action not in ('movement', 'standard')
                or any(type(v) is not int for v in (self.before, self.after, self.speed))
                or self.speed < 1 or self.after < 1 or self.before <= self.after
                or self.before - self.after > self.speed):
            raise ValueError('Invalid one-dimensional approach segment')


def ram_triggered(first: Approach, second: Approach, *, reaction_available: bool,
                  able_to_act: bool) -> bool:
    """Check the conservative contact case after a full-speed approach.

    The caller must establish that these segments are sequential, uninterrupted
    and describe the same straight line in a two-character one-dimensional
    encounter. This helper does not implement a reaction, a hit, damage or Prone.
    """
    if (not isinstance(first, Approach) or not isinstance(second, Approach)
            or type(reaction_available) is not bool or type(able_to_act) is not bool):
        raise ValueError('Invalid Ram trigger input')
    return (reaction_available and able_to_act
            and first.actor == second.actor and first.target == second.target
            and first.turn == second.turn and first.speed == second.speed
            and first.action == 'movement' and second.action == 'standard'
            and first.before - first.after == first.speed
            and first.after == second.before and second.after == 1)
