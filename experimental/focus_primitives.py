"""Isolated Mental Punch resolution; not a battle simulator.

Core pp.33-34, 38, 108. The caller chooses whether the table's shield
multiplier reduction applies to Focus damage; Sturdy is Health-only.
"""

from dataclasses import dataclass

from blacklight.dice import DieRoll, classify
from blacklight.pool_damage import DieSource, roll_damage_pool


@dataclass(frozen=True)
class MentalPunchOutcome:
    total: int
    success: bool
    fantastic: bool
    damage: int
    applied: int
    focus_before: int
    focus_after: int
    demoralized: bool
    shattered: bool
    stunned: bool
    damage_faces: tuple[int, ...]


def resolve_mental_punch(
    roll: DieRoll, damage_rng: DieSource, *, attacker_rank: int, attacker_melee: int,
    target_melee_defense: int, target_focus: int, target_max_focus: int,
    focus_reduction: int = 0, shield_reduction: int = 0,
    attacker_heroic: bool = False,
) -> MentalPunchOutcome:
    """Resolve one close Mental Punch against a living target's Focus.

    `focus_reduction` is only actual Focus DR. `shield_reduction` is an explicit
    table-rule variant, 0 or 2, not the target's Health DR from Sturdy.
    """
    if (attacker_rank < 1 or target_max_focus < 1 or
            target_melee_defense < 0 or focus_reduction < 0 or
            shield_reduction not in (0, 2) or
            target_focus > target_max_focus):
        raise ValueError("Invalid Mental Punch state or reduction")
    check = classify(roll, attacker_melee, target_melee_defense)
    pool = (roll_damage_pool(damage_rng, full_multiplier=attacker_rank,
                             ability=attacker_melee,
                             reduction=focus_reduction + shield_reduction,
                             fantastic=check.fantastic)
            if check.success else None)
    damage = pool.damage if pool is not None else 0
    after = target_focus - damage
    if attacker_heroic and after <= -target_max_focus:
        after = -target_max_focus + 1
    return MentalPunchOutcome(check.total, check.success, check.fantastic,
                              damage, target_focus - after, target_focus,
                              after, after <= 0,
                              after <= -target_max_focus,
                              check.success and check.fantastic,
                              pool.faces if pool is not None else ())
