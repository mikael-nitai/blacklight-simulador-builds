"""Explicit hypotheses for self-incapacitation in the experimental Ram duel."""

from .nonlethal_ram_duel import NonlethalRamProneDuel


class RamIncapacityDuel(NonlethalRamProneDuel):
    """Allow a declared self-damage hypothesis, with automatic end-turn healing.

    This does not declare a table ruling. Death stops end-turn effects; an
    unconscious but living actor receives the existing end-turn effects before
    the first-incapacitation outcome is checked. Both choices are experimental.
    """

    execution_scope = 'experimental_ram_incapacity_duel'

    def __init__(self, *args, self_damage_mode, **kwargs):
        if self_damage_mode not in ('lethal_impact', 'nonlethal_impact'):
            raise ValueError('Choose an explicit experimental self-damage hypothesis')
        self.self_damage_mode = self_damage_mode
        super().__init__(*args, **kwargs)
        if type(self.end_turn_healing_first) is not bool or type(self.stack_stunned_edge) is not bool:
            raise ValueError('Declare boolean timing and stunned-edge variants')
        self._record('incapacity_contract', ('DMG-05', 'POW-03'), mode=self_damage_mode,
                     simultaneous=True, heal_living_at_turn_end=True,
                     healing_first=self.end_turn_healing_first)

    def _ram_self_health(self, attacker, raw_after):
        if self.self_damage_mode == 'nonlethal_impact':
            return max(-attacker.profile.max_health + 1, raw_after)
        return raw_after

    def _ram_self_damage_mode(self):
        return self.self_damage_mode

    def _ram_scope(self):
        return 'experimental bare Ram; simultaneous damage; self-incapacity hypothesis'

    def _end_turn_effects(self, actor):
        fighter = self.fighters[actor]
        def dead():
            if fighter.health > -fighter.profile.max_health:
                return False
            self._record('incapacity_dead', ('DMG-05',), actor=fighter.profile.name,
                         health=fighter.health, mode=self.self_damage_mode)
            return True

        if dead():
            return
        if self.end_turn_healing_first and 'healing_factor' in fighter.profile.powers:
            self._heal(actor, fighter.profile.resilience, 'POW-03')
        if fighter.bleeding:
            before = fighter.health
            damage = max(0, fighter.bleeding - 5 * fighter.profile.health_dr)
            fighter.health -= damage
            fighter.damage_taken += damage
            self._record('condition_tick', ('COND-01', 'POW-02'), actor=fighter.profile.name,
                         condition='bleeding', intensity=fighter.bleeding, damage=damage,
                         health_before=before, health_after=fighter.health)
        if dead():
            return
        if not self.end_turn_healing_first and 'healing_factor' in fighter.profile.powers:
            self._heal(actor, fighter.profile.resilience, 'POW-03')
        if (fighter.conscious and fighter.stunned_by is None and not fighter.shield_active
                and 'shield' in fighter.profile.weapons and fighter.reactions > 0
                and self.policies[actor].use_shield_end_turn(self.observe(actor))):
            fighter.reactions -= 1
            fighter.shield_active = True
            self._record('reaction_spent', ('ACT-03', 'ACT-04', 'HR-04'),
                         actor=fighter.profile.name, source='end_turn', remaining=fighter.reactions)
            self._record('shield_activate', ('HR-04',), actor=fighter.profile.name,
                         cost='reaction', timing='end_turn')
