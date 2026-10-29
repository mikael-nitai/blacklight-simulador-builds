"""Combine two ranged powers with the existing experimental physical host."""

from dataclasses import dataclass

from .double_tap_duel import DoubleTapDuel, DoubleTapPolicy
from .slow_motion_duel import SlowMotionAttackMixin


@dataclass(frozen=True)
class RangedPowersPolicy(DoubleTapPolicy):
    dodge_agility_attacks: bool = True

    def __post_init__(self):
        super().__post_init__()
        if type(self.dodge_agility_attacks) is not bool:
            raise ValueError('Slow-Motion Dodge preference must be boolean')

    def choose_slow_motion_dodge(self, observation):
        return self.dodge_agility_attacks


class RangedPowersDuel(SlowMotionAttackMixin, DoubleTapDuel):
    execution_scope = 'experimental_double_tap_slow_motion_ram_prone_duel'
    additional_experimental_powers = frozenset({'double_tap', 'slow_motion_dodge'})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if any(not callable(getattr(policy, 'choose_slow_motion_dodge', None))
               for policy in self.policies):
            raise ValueError('Both policies must explicitly decide whether to dodge')
