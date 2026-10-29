"""Combine the current Ram self-incapacitation ruling with ranged powers."""

from .ram_incapacity_duel import RamIncapacityMixin
from .stopping_duel import StoppingDuel


class StoppingRamDuel(RamIncapacityMixin, StoppingDuel):
    """Apply both impacts, stop before healing for the declared character.

    The undecided death threshold and an unconfirmed other attacker's
    self-incapacitation still abort the duel; never silently drop the failure.
    """

    execution_scope = 'experimental_stopping_ram_table_ruling_duel'

    def __init__(self, *args, stop_on_attacker, **kwargs):
        super().__init__(*args, self_damage_mode='stop_before_heal_reject_lethal',
                         stop_on_attacker=stop_on_attacker, **kwargs)
