"""Single-target submachine gun in the experimental ranged powers host."""

from dataclasses import replace

from .ranged_powers_duel import RangedPowersDuel


class SubmachineDuel(RangedPowersDuel):
    """Explicit per-combatant equipment; no multi-target spray is implemented."""

    execution_scope = 'experimental_single_target_submachine_duel'

    def __init__(self, *args, ranged_weapons, **kwargs):
        if (not isinstance(ranged_weapons, tuple) or len(ranged_weapons) != 2
                or any(weapon not in ('generic', 'submachine_gun') for weapon in ranged_weapons)):
            raise ValueError('Declare each combatant ranged weapon explicitly')
        self.ranged_weapons = ranged_weapons
        super().__init__(*args, **kwargs)
        for fighter, weapon in zip(self.fighters, ranged_weapons):
            p = fighter.profile
            if weapon == 'submachine_gun' and (p.ranged_range != 10 or not p.ranged_is_ammunition
                                                or p.ranged_bonus < 1):
                raise ValueError('Submachine gun requires range 10, ammunition and at least +1 bonus')

    def _attack_check_spec(self, actor, kind, target_actor=None):
        spec = super()._attack_check_spec(actor, kind, target_actor)
        if (kind == 'ranged' and self.ranged_weapons[actor] == 'submachine_gun'
                and self._distance_between(actor, self._target_index(actor, target_actor)) <= 5):
            spec = replace(spec, troubles=spec.troubles + 1)
        return spec

    def _prepare_attack_check(self, actor, kind, spec=None, *, target_actor=None):
        target = self._target_index(actor, target_actor)
        if (kind == 'ranged' and self.ranged_weapons[actor] == 'submachine_gun'
                and self._distance_between(actor, target) <= 5):
            self._record('smg_close_check', ('CORE-P36-SMG',), actor=self.fighters[actor].profile.name,
                         target=self.fighters[target].profile.name, trigger=self.trigger_seq + 1,
                         distance=self._distance_between(actor, target), added_troubles=1)
        return super()._prepare_attack_check(actor, kind, spec, target_actor=target)
