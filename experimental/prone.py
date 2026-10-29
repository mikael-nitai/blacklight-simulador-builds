"""Experimental primitives for Prone; deliberately not connected to combat."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProneModifiers:
    edges: int
    troubles: int


def attack_modifiers(*, attacker_prone: bool, target_prone: bool,
                     ability: str, attack_range: str) -> ProneModifiers:
    """Return condition contributions; the caller combines all edge/trouble sources."""
    if (type(attacker_prone) is not bool or type(target_prone) is not bool
            or ability not in ('melee', 'agility', 'resilience', 'vigilance', 'ego', 'logic')
            or attack_range not in ('close', 'ranged')):
        raise ValueError('Invalid Prone attack context')
    return ProneModifiers(edges=int(target_prone and attack_range == 'close'),
                          troubles=int(attacker_prone and ability == 'melee')
                          + int(target_prone and attack_range == 'ranged'))


def stand(*, prone: bool, movement_remaining: int, can_move: bool) -> tuple[bool, int]:
    """Stand for one space of available movement, if the caller permits movement."""
    if (type(prone) is not bool or type(can_move) is not bool
            or type(movement_remaining) is not int or movement_remaining < 0):
        raise ValueError('Invalid movement state')
    if not prone or not can_move or movement_remaining < 1:
        raise ValueError('Standing is not available')
    return False, movement_remaining - 1
