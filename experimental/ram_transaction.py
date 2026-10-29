"""Isolated Ram transaction for synthetic checks; not a duel engine."""

from dataclasses import dataclass

from .ram_impact import RamImpact, ram_impact
from .ram_trigger import Approach, ram_triggered


@dataclass(frozen=True)
class RamState:
    attacker_health: int
    target_health: int
    reactions: int
    attacker_able: bool
    target_prone: bool

    def __post_init__(self):
        if (any(type(value) is not int for value in
                (self.attacker_health, self.target_health, self.reactions))
                or self.reactions < 0 or type(self.attacker_able) is not bool
                or type(self.target_prone) is not bool):
            raise ValueError('Invalid synthetic Ram state')


@dataclass(frozen=True)
class RamTransaction:
    before: RamState
    after: RamState
    impact: RamImpact
    self_pool: str


def execute_ram(state: RamState, first: Approach, second: Approach, *,
                success: bool, fantastic_success: bool, full_dice: int,
                ability: int, target_reduction: int, attacker_reduction: int,
                target_faces: tuple[int, ...], self_pool: str,
                attacker_faces: tuple[int, ...] | None = None) -> RamTransaction:
    """Apply one synthetic reaction to immutable data, or reject without mutation.

    The caller establishes straight-line continuity and supplies an already
    resolved attack check and already rolled faces. This intentionally models
    simultaneous proposed health losses without Heroic, Shield, Riposte, weapon
    effects or other condition interactions. It is not connected to combat.
    """
    if not isinstance(state, RamState):
        raise ValueError('A valid synthetic state is required')
    if (state.attacker_health <= 0 or state.target_health <= 0
            or not ram_triggered(first, second, reaction_available=state.reactions > 0,
                                 able_to_act=state.attacker_able)):
        raise ValueError('Ram is not available in this synthetic state')
    impact = ram_impact(success=success, fantastic_success=fantastic_success,
                        full_dice=full_dice, ability=ability,
                        target_reduction=target_reduction, attacker_reduction=attacker_reduction,
                        target_faces=target_faces, self_pool=self_pool, attacker_faces=attacker_faces)
    after_health = state.attacker_health - impact.attacker_damage
    after = RamState(attacker_health=after_health,
                     target_health=state.target_health - impact.target_damage,
                     reactions=state.reactions - 1, attacker_able=state.attacker_able and after_health > 0,
                     target_prone=state.target_prone or impact.target_prone)
    return RamTransaction(state, after, impact, self_pool)
