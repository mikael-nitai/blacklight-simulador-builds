"""Health/Focus damage arithmetic. Rule IDs: DMG-01/02/03."""

from math import ceil
from typing import Iterable


def calculate(
    marvel_face: int,
    base_rank: int,
    ability: int,
    bonus_candidates: Iterable[int],
    reduction: int,
    fantastic: bool,
    *,
    numerator: int = 1,
    denominator: int = 1,
) -> int:
    """Apply DR to the multiplier first, then double or divide final damage.

    `numerator/denominator` is for a specific power's replacement result, e.g.
    Fast Strikes half damage. The FAQ example rounds a fractional half upward.
    """
    if not 1 <= marvel_face <= 6 or base_rank < 1 or reduction < 0:
        raise ValueError("Invalid damage input")
    if numerator < 0 or denominator <= 0:
        raise ValueError("Invalid damage fraction")
    candidates = tuple(bonus_candidates)
    if any(bonus < 0 for bonus in candidates):
        raise ValueError("Damage bonuses cannot be negative")
    multiplier = base_rank + max((0, *candidates)) - reduction
    if multiplier < 1:
        return 0
    marvel_value = 6 if marvel_face == 1 else marvel_face
    regular = max(0, marvel_value * multiplier + ability)
    return ceil(regular * (2 if fantastic else 1) * numerator / denominator)
