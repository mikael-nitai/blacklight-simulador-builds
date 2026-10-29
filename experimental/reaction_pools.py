"""Experimental ordinary/restricted reaction accounting for Fast Hands.

Core p.99 (PDF p.100): one extra reaction per round usable only to trigger
a Ranged Weapons power. Same-trigger restriction: FAQ, p.5.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReactionPools:
    ordinary: int
    fast_hands: int
    spent_triggers: frozenset[int] = frozenset()

    def __post_init__(self):
        if (type(self.ordinary) is not int or type(self.fast_hands) is not int
                or self.ordinary < 0 or self.fast_hands not in (0, 1)
                or not isinstance(self.spent_triggers, frozenset)
                or any(type(trigger) is not int or trigger < 1 for trigger in self.spent_triggers)):
            raise ValueError('Invalid reaction pools')


def start_round(*, combat_reflexes: bool, fast_hands: bool) -> ReactionPools:
    """Use the current simulator's conservative start-of-round reset convention."""
    if type(combat_reflexes) is not bool or type(fast_hands) is not bool:
        raise ValueError('Reaction traits must be explicit boolean values')
    return ReactionPools(1 + int(combat_reflexes), int(fast_hands))


def spend_reaction(state: ReactionPools, *, pool: str, trigger: int,
                   power_set: str, can_react: bool) -> ReactionPools:
    """Spend the chosen pool once for a trigger; reject all illegal uses.

    The host supplies the power's verified set and legal timing. Ordinary
    reactions can be used by any legal reaction; the restricted reaction is
    valid only for a Ranged Weapons power.
    """
    if (not isinstance(state, ReactionPools) or pool not in ('ordinary', 'fast_hands')
            or type(trigger) is not int or trigger < 1 or type(can_react) is not bool
            or not isinstance(power_set, str) or not power_set):
        raise ValueError('Invalid reaction request')
    if (not can_react or trigger in state.spent_triggers
            or pool == 'ordinary' and state.ordinary == 0
            or pool == 'fast_hands' and (state.fast_hands == 0 or power_set != 'ranged_weapons')):
        raise ValueError('Reaction is not available for this trigger and pool')
    return ReactionPools(state.ordinary - int(pool == 'ordinary'),
                         state.fast_hands - int(pool == 'fast_hands'),
                         state.spent_triggers | {trigger})
