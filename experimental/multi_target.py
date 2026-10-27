"""Table-rule Fast Strikes damage for one or two distinct targets.

This is an isolated, deterministic group-combat primitive, not a full group
turn engine. Biological-weapon effects and reactions to the shared trigger are
deliberately outside its contract pending explicit group rules. One target
receives two components, as confirmed by the user. Two targets receive one
component each as a conservative extension.
"""

from dataclasses import dataclass

from blacklight.dice import DieRoll, classify
from blacklight.pool_damage import DieSource, roll_damage_pool


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
    damage_faces: tuple[tuple[int, ...], ...]


def resolve_fast_strikes(
    roll: DieRoll,
    damage_rng: DieSource,
    *,
    melee_modifier: int,
    rank: int,
    damage_ability: int,
    bonus_candidates: tuple[int, ...],
    targets: tuple[Target, ...],
    fast_zero_dice_bonus: bool = False,
) -> tuple[TargetOutcome, ...]:
    """Apply one finalized Melee roll separately to one or two distinct targets.

    The caller handles edge/trouble before passing `roll`. A single target
    receives two independently rolled damage components; two distinct targets
    receive one each. DR and Fast halving apply to each component separately.
    """
    if not 1 <= len(targets) <= 2 or len({t.name for t in targets}) != len(targets):
        raise ValueError("Fast Strikes requires one or two distinct targets")
    outcomes = []
    for target in targets:
        check = classify(roll, melee_modifier, target.melee_defense)
        faces: tuple[tuple[int, ...], ...] = ()
        damage = 0
        if check.success:
            pools = tuple(roll_damage_pool(
                damage_rng, full_multiplier=rank + max(0, *bonus_candidates),
                ability=damage_ability, reduction=target.reduction,
                fast_strikes=True, fantastic=check.fantastic,
                fast_zero_dice_bonus=fast_zero_dice_bonus)
                for _ in range(2 if len(targets) == 1 else 1))
            faces = tuple(pool.faces for pool in pools)
            damage = sum(pool.damage for pool in pools)
        outcomes.append(TargetOutcome(
            target.name, target.melee_defense, check.total, check.success,
            check.fantastic, damage, target.health, target.health - damage,
            faces))
    return tuple(outcomes)
