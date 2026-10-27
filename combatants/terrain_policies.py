"""Policies use visible geometry; no rules or dice are resolved here."""

from dataclasses import dataclass

from blacklight.engine import Action
from .split_fast import SplitFastPolicy


@dataclass(frozen=True)
class WallAwarePolicy(SplitFastPolicy):
    """Keep the base priorities, but shoot instead of spending a blocked retreat.

    This is a limited competence improvement, not an optimal terrain solver.
    """
    def choose_action(self, observation):
        request = super().choose_action(observation)
        terrain = observation.terrain
        if (terrain is not None and terrain.kind == 'corridor'
                and request.kind == 'move' and request.move is not None
                and request.move.direction == 'retreat'):
            x, other = terrain.me[0], terrain.foe[0]
            available = x if x < other else terrain.size[0] - 1 - x
            if (available == 0 and observation.me.ranged_range
                    and observation.distance <= 2 * observation.me.ranged_range):
                return Action('ranged')
        return request
