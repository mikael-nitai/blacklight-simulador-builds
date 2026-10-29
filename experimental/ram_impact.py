"""Experimental Ram damage hypotheses, separate from the certified engine.

Inputs are already rolled damage faces; this module does not make an attack,
spend a reaction, decide Shield timing, or mutate fighters.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RamImpact:
    target_regular: int
    attacker_regular: int
    target_damage: int
    attacker_damage: int
    target_prone: bool


def ram_impact(*, success: bool, fantastic_success: bool, full_dice: int,
               ability: int, target_reduction: int, attacker_reduction: int,
               target_faces: tuple[int, ...], self_pool: str,
               attacker_faces: tuple[int, ...] | None = None) -> RamImpact:
    """Evaluate explicitly selected hypotheses for the attacker's impact pool.

    ``shared`` reuses the same ordered full pool for both recipients; ``separate``
    supplies a second full pool. Each recipient's reduction removes dice before
    damage is multiplied. These hypotheses are NOT a ruling on the Core's
    ambiguous impact details or how the table handles biological weapons.
    """
    if (type(success) is not bool or type(fantastic_success) is not bool
            or fantastic_success and not success
            or any(type(value) is not int for value in
                   (full_dice, ability, target_reduction, attacker_reduction))
            or min(full_dice, target_reduction, attacker_reduction) < 0
            or self_pool not in ('shared', 'separate')):
        raise ValueError('Invalid Ram impact parameters')

    def valid_faces(faces, count):
        return (isinstance(faces, tuple) and len(faces) == count
                and all(type(face) is int and 1 <= face <= 6 for face in faces))

    count = full_dice if success else 0
    if not valid_faces(target_faces, count):
        raise ValueError('Target pool must contain the declared number of d6 faces')
    if self_pool == 'shared':
        if attacker_faces is not None:
            raise ValueError('Shared impact must reuse the declared target pool')
        own_faces = target_faces
    else:
        if not valid_faces(attacker_faces, count):
            raise ValueError('Separate impact must declare its own complete pool')
        own_faces = attacker_faces
    if not success:
        return RamImpact(0, 0, 0, 0, False)

    def regular(faces, reduction):
        count_after = max(0, full_dice - reduction)
        if not count_after:
            return 0
        return max(0, sum(6 if face == 1 else face for face in faces[:count_after]) + ability)

    target = regular(target_faces, target_reduction)
    attacker = regular(own_faces, attacker_reduction)
    return RamImpact(target, attacker, target * (3 if fantastic_success else 2),
                     attacker, fantastic_success)
