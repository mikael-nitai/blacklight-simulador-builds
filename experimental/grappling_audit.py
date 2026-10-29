"""Independent state arithmetic checks for the isolated grappling experiment.

The attack hit and applied damage must be audited against the host separately.
"""

from dataclasses import replace

from blacklight.dice import DieRoll, RerollTrace
from blacklight.dice_audit import audit_rerolls
from .grappling import EscapeResult, GrapplingResult
from .reaction_pools import ReactionPools


def audit_grappling(result, *, has_power, attack_success, fantastic_success, applied_damage, trigger):
    if not isinstance(result, GrapplingResult):
        return ['Invalid grapple result']
    b, a = result.before, result.after
    issues = []
    if (has_power is not True or b.attacker_rank < 2 or b.attacker_focus < 6
            or not b.attacker_standard or not b.attacker_conscious or b.attacker_stunned
            or b.target_health <= 0 or b.distance != 1 or b.grabbed
            or type(attack_success) is not bool or type(fantastic_success) is not bool
            or fantastic_success and not attack_success or type(applied_damage) is not int
            or applied_damage < 0 or not attack_success and applied_damage != 0
            or type(trigger) is not int or trigger < 1):
        issues.append('Invalid independent grapple facts')
        return issues
    if (type(result.attack_success) is not bool or type(result.fantastic_success) is not bool
            or type(result.applied_damage) is not int or type(result.trigger) is not int
            or (result.attack_success, result.fantastic_success, result.applied_damage, result.trigger)
            != (attack_success, fantastic_success, applied_damage, trigger)):
        issues.append('Grapple facts differ from host')
    expected = replace(b, attacker_focus=b.attacker_focus - 5, attacker_standard=False,
                       target_health=b.target_health - applied_damage, grabbed=attack_success,
                       pinned=fantastic_success)
    if a != expected:
        issues.append('Grapple resource or condition transition mismatch')
    return issues


def audit_escape(result, *, melee, mighty, grabber_melee_defense, timing, trigger):
    if not isinstance(result, EscapeResult):
        return ['Invalid escape result']
    b, a = result.before, result.after
    if (any(type(v) is not int for v in (melee, mighty, grabber_melee_defense))
            or mighty < 0 or grabber_melee_defense < 0 or timing not in ('reaction', 'standard')
            or timing == 'standard' and trigger is not None
            or timing == 'reaction' and (type(trigger) is not int or trigger < 1)):
        return ['Invalid independent escape facts']
    if (not b.grabbed or b.target_health <= 0 or b.target_stunned
            or timing == 'standard' and not b.target_standard):
        return ['Escape unavailable']
    if (timing == 'reaction' and
            (b.target_reactions.ordinary < 1 or trigger in b.target_reactions.spent_triggers)):
        return ['Escape reaction unavailable']
    if (not isinstance(result.roll, DieRoll) or not isinstance(result.rerolls, tuple)
            or any(not isinstance(trace, RerollTrace) for trace in result.rerolls)):
        return ['Invalid recorded escape dice']
    roll = result.roll
    fields = (roll.left, roll.marvel, roll.right)
    troubles = int(b.pinned)
    issues = audit_rerolls({'roll': list(fields), 'rerolls': [vars(r) for r in result.rerolls]},
                           edges=0, troubles=troubles)
    total = fields[0] + (6 if fields[1] == 1 else fields[1]) + fields[2] + melee + mighty
    succeeded = fields == (6, 1, 6) or total >= grabber_melee_defense
    if (type(result.modifier) is not int or type(result.target_number) is not int
            or type(result.troubles) is not int or type(result.total) is not int
            or type(result.success) is not bool
            or (result.timing, result.modifier, result.target_number, result.troubles,
         result.total, result.success, result.trigger)
            != (timing, melee + mighty, grabber_melee_defense, troubles, total, succeeded, trigger)):
        issues.append('Escape roll or classification mismatch')
    reactions = b.target_reactions
    if timing == 'reaction':
        reactions = ReactionPools(reactions.ordinary - 1, reactions.fast_hands,
                                  reactions.spent_triggers | {trigger})
    expected = replace(b, target_standard=b.target_standard if timing == 'reaction' else False,
                       target_reactions=reactions, grabbed=not succeeded,
                       pinned=b.pinned and not succeeded)
    if a != expected:
        issues.append('Escape resource or condition transition mismatch')
    return issues
