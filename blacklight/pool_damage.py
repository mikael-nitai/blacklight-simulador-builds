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
    counterfactual_faces: tuple[int, ...] = ()
    damage_without_reduction: int | None = None


def roll_damage_pool(rng: DieSource, *, full_multiplier: int,
                     ability: int, reduction: int = 0,
                     fast_strikes: bool = False,
                     fantastic: bool = False,
                     sample_counterfactual: bool = False) -> PoolDamage:
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
    faces = tuple(rng.randint(1, 6) for _ in range(count))

    def value(rolled: tuple[int, ...], bonus: int) -> int:
        if not rolled:
            return 0
        total = max(0, sum(6 if face == 1 else face for face in rolled)
                    + bonus)
        return total * (2 if fantastic and not fast_strikes else 1)

    total = value(faces, added)
    extra: tuple[int, ...] = ()
    without_reduction: int | None = None
    if sample_counterfactual:
        raw_count = (full_multiplier if fantastic or not fast_strikes
                     else full_multiplier // 2)
        extra = tuple(rng.randint(1, 6)
                      for _ in range(max(0, raw_count - count)))
        without_reduction = value(faces + extra,
                                  ability if fantastic or not fast_strikes
                                  else ability // 2)
    return PoolDamage(full_multiplier, reduction, after_dr,
                      count, added if count else 0, faces, total,
                      extra, without_reduction)
