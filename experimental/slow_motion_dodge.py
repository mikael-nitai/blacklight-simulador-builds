"""Experimental contract for Slow-Motion Dodge, not yet a duel integration.

Core Rulebook printed p. 118 (PDF p. 119): an enemy attacks the character's
Agility defense; a reaction gives that attack one trouble.  The caller is
responsible for establishing the actual defense and whether reactions are legal.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class DodgeTrigger:
    has_power: bool
    enemy_attack: bool
    defense: str
    before_roll: bool
    can_react: bool
    reactions_remaining: int
    already_reacted: bool

    def __post_init__(self):
        flags = (self.has_power, self.enemy_attack, self.before_roll,
                 self.can_react, self.already_reacted)
        if (any(type(value) is not bool for value in flags)
                or self.defense not in ('melee', 'agility', 'resilience', 'vigilance', 'ego', 'logic')
                or type(self.reactions_remaining) is not int or self.reactions_remaining < 0):
            raise ValueError('Invalid Slow-Motion Dodge trigger')


@dataclass(frozen=True)
class DodgeResolution:
    activated: bool
    reactions_remaining: int
    added_troubles: int
    reacted_to_trigger: bool


def can_use_slow_motion_dodge(trigger: DodgeTrigger) -> bool:
    if not isinstance(trigger, DodgeTrigger):
        raise ValueError('An explicit attack trigger is required')
    return (trigger.has_power and trigger.enemy_attack and trigger.defense == 'agility'
            and trigger.before_roll and trigger.can_react
            and trigger.reactions_remaining > 0 and not trigger.already_reacted)


def resolve_slow_motion_dodge(trigger: DodgeTrigger, *, activate: bool) -> DodgeResolution:
    """Spend one ordinary reaction before the roll, or leave the state unchanged.

    The result contributes exactly one trouble; combining it with other edges
    and troubles, rolling dice, and enforcing per-attack identity are the host's
    responsibilities.  Activating on an invalid trigger raises rather than
    silently consuming a reaction or modifying a previously rolled attack.
    """
    if not isinstance(trigger, DodgeTrigger) or type(activate) is not bool:
        raise ValueError('Provide a valid trigger and explicit activation decision')
    if activate and not can_use_slow_motion_dodge(trigger):
        raise ValueError('Slow-Motion Dodge is unavailable for this attack')
    return DodgeResolution(activate, trigger.reactions_remaining - int(activate),
                           int(activate), trigger.already_reacted or activate)
