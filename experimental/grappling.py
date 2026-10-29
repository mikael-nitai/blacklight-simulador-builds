"""Deterministic isolated Grappling Technique, Grabbed and Escape transactions.

This is not a battle host. The caller resolves the attack and damage and
supplies the post-reroll dice for an escape; no random source is consulted.
"""

from dataclasses import dataclass, replace

from blacklight.dice import DieRoll, RerollTrace, classify
from blacklight.dice_audit import audit_rerolls
from .reaction_pools import ReactionPools, spend_reaction


@dataclass(frozen=True)
class GrapplingState:
    attacker_rank: int
    attacker_focus: int
    attacker_standard: bool
    attacker_conscious: bool
    attacker_stunned: bool
    target_health: int
    target_standard: bool
    target_stunned: bool
    target_reactions: ReactionPools
    distance: int
    grabbed: bool = False
    pinned: bool = False

    def __post_init__(self):
        flags = (self.attacker_standard, self.attacker_conscious, self.attacker_stunned, self.target_standard,
                 self.target_stunned, self.grabbed, self.pinned)
        if (any(type(v) is not bool for v in flags)
                or any(type(v) is not int for v in (self.attacker_rank, self.attacker_focus,
                                                      self.target_health, self.distance))
                or self.attacker_rank < 1 or self.attacker_focus < 0 or self.distance < 1
                or not isinstance(self.target_reactions, ReactionPools)
                or self.pinned and not self.grabbed or self.grabbed and self.distance != 1):
            raise ValueError('Invalid grappling state')


@dataclass(frozen=True)
class GrapplingResult:
    before: GrapplingState
    after: GrapplingState
    attack_success: bool
    fantastic_success: bool
    applied_damage: int
    trigger: int


def grappling_technique(state, *, has_power, attack_success, fantastic_success,
                         applied_damage, trigger):
    """Spend a standard action and 5 Focus; apply an externally resolved hit.

    The host must validate the d616 attack and damage independently, including
    shield and reduction. A zero-damage hit still applies the condition. This
    initial transaction rejects repeated holds and reach beyond one space.
    """
    if (not isinstance(state, GrapplingState)
            or any(type(v) is not bool for v in (has_power, attack_success, fantastic_success))
            or type(applied_damage) is not int or applied_damage < 0
            or type(trigger) is not int or trigger < 1
            or fantastic_success and not attack_success
            or not attack_success and applied_damage != 0):
        raise ValueError('Invalid grappling attack facts')
    if (not has_power or state.attacker_rank < 2 or state.attacker_focus < 6
            or not state.attacker_standard or not state.attacker_conscious or state.attacker_stunned
            or state.target_health <= 0 or state.distance != 1 or state.grabbed):
        raise ValueError('Grappling Technique is not available')
    after = replace(state, attacker_focus=state.attacker_focus - 5, attacker_standard=False,
                    target_health=state.target_health - applied_damage,
                    grabbed=attack_success, pinned=fantastic_success)
    return GrapplingResult(state, after, attack_success, fantastic_success, applied_damage, trigger)


@dataclass(frozen=True)
class EscapeResult:
    before: GrapplingState
    after: GrapplingState
    timing: str
    modifier: int
    target_number: int
    troubles: int
    roll: DieRoll
    rerolls: tuple
    total: int
    success: bool
    trigger: int | None


def escape(state, *, timing, melee, mighty, grabber_melee_defense, roll, rerolls,
           trigger=None):
    """Resolve Escape with its actual Melee score, Mighty and pinned trouble.

    Reroll history is checked independently; external edges and other condition
    modifiers are outside this initial scope. The host supplies a trigger ID
    for a reaction and decides whether it coincides with a prior shield trigger.
    """
    if (not isinstance(state, GrapplingState) or timing not in ('standard', 'reaction')
            or any(type(v) is not int for v in (melee, mighty, grabber_melee_defense))
            or mighty < 0 or grabber_melee_defense < 0 or not isinstance(roll, DieRoll)
            or not isinstance(rerolls, tuple) or any(not isinstance(v, RerollTrace) for v in rerolls)
            or timing == 'standard' and trigger is not None
            or timing == 'reaction' and (type(trigger) is not int or trigger < 1)):
        raise ValueError('Invalid escape request')
    if (not state.grabbed or state.target_health <= 0 or state.target_stunned
            or timing == 'standard' and not state.target_standard):
        raise ValueError('Escape is unavailable')
    troubles = int(state.pinned)
    event = {'roll': [roll.left, roll.marvel, roll.right], 'rerolls': [vars(v) for v in rerolls]}
    if audit_rerolls(event, edges=0, troubles=troubles):
        raise ValueError('Escape roll does not have the required trouble history')
    check = classify(roll, melee + mighty, grabber_melee_defense)
    reactions = state.target_reactions
    if timing == 'reaction':
        reactions = spend_reaction(reactions, pool='ordinary', trigger=trigger,
                                   power_set='basic', can_react=True)
    after = replace(state, target_standard=state.target_standard if timing == 'reaction' else False,
                    target_reactions=reactions, grabbed=not check.success,
                    pinned=state.pinned and not check.success)
    return EscapeResult(state, after, timing, melee + mighty, grabber_melee_defense,
                        troubles, roll, rerolls, check.total, check.success, trigger)


def pinned_check_trouble(state, actor, ability):
    """Pinned adds one trouble to the victim's Melee or Agility checks."""
    if (not isinstance(state, GrapplingState) or actor not in ('attacker', 'target')
            or ability not in ('melee', 'agility', 'resilience', 'vigilance', 'ego', 'logic')):
        raise ValueError('Invalid pinned check query')
    return int(state.pinned and actor == 'target' and ability in ('melee', 'agility'))


def movement_allowed(state, actor, *, carrying=False):
    """Reject unresolved carrying; neither participant otherwise moves in a hold."""
    if (not isinstance(state, GrapplingState) or actor not in ('attacker', 'target')
            or type(carrying) is not bool):
        raise ValueError('Invalid movement query')
    if carrying:
        raise ValueError('Carrying an entangled combatant is outside this experiment')
    return not state.grabbed


def release(state, actor):
    if (not isinstance(state, GrapplingState) or actor != 'attacker' or not state.grabbed
            or not state.attacker_conscious or state.attacker_stunned):
        raise ValueError('Only the grabber can release an active hold')
    return replace(state, grabbed=False, pinned=False)
