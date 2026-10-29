"""Experimental Point-Blank Parry trigger and resource transaction.

Core p.112 (PDF p.113); the returned transaction does not roll or inflict damage.
"""

from dataclasses import dataclass
from .reaction_pools import ReactionPools, spend_reaction


@dataclass(frozen=True)
class ParryTrigger:
    has_power: bool
    rank: int
    enemy_attack: bool
    attack_missed: bool
    target_was_user: bool
    distance: int
    focus: int
    has_ranged_weapon: bool
    can_react: bool
    trigger: int

    def __post_init__(self):
        flags = (self.has_power, self.enemy_attack, self.attack_missed, self.target_was_user,
                 self.has_ranged_weapon, self.can_react)
        if (any(type(value) is not bool for value in flags)
                or any(type(value) is not int for value in (self.rank, self.distance, self.focus, self.trigger))
                or self.rank < 1 or self.distance < 1 or self.focus < 0 or self.trigger < 1):
            raise ValueError('Invalid Point-Blank Parry trigger')


@dataclass(frozen=True)
class ParryTransaction:
    focus_after: int
    reactions_after: ReactionPools
    ranged_attack_pending: bool


def point_blank_parry(trigger: ParryTrigger, reactions: ReactionPools, *, pool: str) -> ParryTransaction:
    """Consume one legal reaction and 5 Focus; the caller resolves the ranged attack.

    This conservative host requires an available ranged weapon, 1-2 spaces,
    Rank 2+, and at least 1 Focus after payment. Once the caller resolves a hit,
    it applies normal damage or double damage plus Bleeding on a Fantastic
    success, respecting any applicable immunity. No dice or damage are rolled
    here and attack ordering is controlled by the battle host.
    """
    if (not isinstance(trigger, ParryTrigger) or not trigger.has_power or trigger.rank < 2
            or not trigger.enemy_attack or not trigger.attack_missed or not trigger.target_was_user
            or trigger.distance > 2 or trigger.focus < 6 or not trigger.has_ranged_weapon
            or not trigger.can_react):
        raise ValueError('Point-Blank Parry is unavailable')
    after = spend_reaction(reactions, pool=pool, trigger=trigger.trigger,
                           power_set='ranged_weapons', can_react=trigger.can_react)
    return ParryTransaction(trigger.focus - 5, after, True)
