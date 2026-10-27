"""Literal Marvel-die damage pool specified by the Blacklight table.

The caller supplies the full multiplier for one weapon. Each die is an
independent d6 whose face 1 contributes 6 damage. A standard Fantastic doubles
the rolled total; Fast Strikes instead uses full components on Fantastic and
halves the dice count and ability bonus before rolling on ordinary success.
"""

from dataclasses import dataclass
from typing import Protocol


class DieSource(Protocol):
    def randint(self, low: int, high: int) -> int: ...


@dataclass(frozen=True)
class PoolDamage:
    full_multiplier: int
    reduction: int
    dice_after_reduction: int
    dice_rolled: int
    ability_added: int
    faces: tuple[int, ...]
    damage: int


def roll_damage_pool(rng: DieSource, *, full_multiplier: int,
                     ability: int, reduction: int = 0,
                     fast_strikes: bool = False,
                     fantastic: bool = False) -> PoolDamage:
    """Roll one weapon's damage after DR; no hit check is performed here."""
    if full_multiplier < 0 or reduction < 0 or not isinstance(ability, int):
        raise ValueError("Invalid damage-pool inputs")
    after_dr = max(0, full_multiplier - reduction)
    if fast_strikes and not fantastic:
        if ability % 2:
            raise ValueError("Half an odd ability bonus needs a table ruling")
        count = after_dr // 2
        added = ability // 2
    else:
        count = after_dr
        added = ability
    if count < 1:
        return PoolDamage(full_multiplier, reduction, after_dr,
                          0, 0, (), 0)
    faces = tuple(rng.randint(1, 6) for _ in range(count))
    values = tuple(6 if face == 1 else face for face in faces)
    total = max(0, sum(values) + added)
    if fantastic and not fast_strikes:
        total *= 2
    return PoolDamage(full_multiplier, reduction, after_dr,
                      count, added, faces, total)
