"""Official Fast Strikes damage against up to two distinct targets.

This is an isolated, deterministic group-combat primitive, not a full group
turn engine. Biological-weapon effects and reactions to the shared trigger are
deliberately outside its contract pending explicit group rules.
"""

from dataclasses import dataclass

from blacklight.damage import calculate
from blacklight.dice import DieRoll, classify


@dataclass(frozen=True)
class Target:
    name: str
    melee_defense: int
    health: int
    reduction: int = 0

    def __post_init__(self) -> None:
        if not self.name or self.reduction < 0:
            raise ValueError("Target must have a name and nonnegative reduction")


@dataclass(frozen=True)
class TargetOutcome:
    target: str
    defense: int
    total: int
    success: bool
    fantastic: bool
    damage: int
    health_before: int
    health_after: int


def resolve_fast_strikes(
    roll: DieRoll,
    *,
    melee_modifier: int,
    rank: int,
    damage_ability: int,
    bonus_candidates: tuple[int, ...],
    targets: tuple[Target, ...],
) -> tuple[TargetOutcome, ...]:
    """Apply one finalized Melee roll separately to one or two distinct targets.

    The caller handles edge/trouble before passing `roll`. A regular hit deals
    half regular damage, rounded up, after each target's DR. A Fantastic hit
    deals full regular damage, with no default doubling or bonus attack.
    """
    if not 1 <= len(targets) <= 2 or len({t.name for t in targets}) != len(targets):
        raise ValueError("Fast Strikes requires one or two distinct targets")
    outcomes = []
    for target in targets:
        check = classify(roll, melee_modifier, target.melee_defense)
        damage = (calculate(roll.marvel, rank, damage_ability,
                            bonus_candidates, target.reduction, False,
                            denominator=1 if check.fantastic else 2)
                  if check.success else 0)
        outcomes.append(TargetOutcome(
            target.name, target.melee_defense, check.total, check.success,
            check.fantastic, damage, target.health, target.health - damage))
    return tuple(outcomes)
