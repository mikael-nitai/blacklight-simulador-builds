"""Explicit hypotheses for self-incapacitation in the experimental Ram duel."""

from blacklight.engine import IllegalAction
from .nonlethal_ram_duel import NonlethalRamProneDuel


class RamIncapacityDuel(NonlethalRamProneDuel):
    """Allow a declared self-damage and end-of-combat convention.

    The historical lethal/nonlethal hypotheses heal a living unconscious actor
    at turn end. The separately selected current table mode ends the encounter
    before that healing and refuses the unresolved self-death boundary.
    """

    execution_scope = 'experimental_ram_incapacity_duel'

    def __init__(self, *args, self_damage_mode, stop_on_attacker=None, **kwargs):
        if self_damage_mode not in ('lethal_impact', 'nonlethal_impact', 'stop_before_heal_reject_lethal'):
            raise ValueError('Choose an explicit experimental self-damage hypothesis')
        self.self_damage_mode = self_damage_mode
        self.stop_on_attacker = stop_on_attacker
        self._ram_incapacitated_actor = None
        super().__init__(*args, **kwargs)
        if (self_damage_mode == 'stop_before_heal_reject_lethal'
                and (not isinstance(stop_on_attacker, str)
                     or stop_on_attacker not in {fighter.profile.name for fighter in self.fighters})):
            raise ValueError('Identify the attacker covered by the table ruling')
        if self_damage_mode != 'stop_before_heal_reject_lethal' and stop_on_attacker is not None:
            raise ValueError('The stop attacker applies only to the table-ruling mode')
        if type(self.end_turn_healing_first) is not bool or type(self.stack_stunned_edge) is not bool:
            raise ValueError('Declare boolean timing and stunned-edge variants')
        self._record('incapacity_contract', ('DMG-05', 'POW-03'), mode=self_damage_mode,
                     simultaneous=True,
                     heal_living_at_turn_end=self_damage_mode != 'stop_before_heal_reject_lethal',
                     healing_first=self.end_turn_healing_first,
                     **({'stop_on_attacker': stop_on_attacker}
                        if self_damage_mode == 'stop_before_heal_reject_lethal' else {}))

    def _ram_self_health(self, attacker, raw_after):
        if self.self_damage_mode == 'nonlethal_impact':
            return max(-attacker.profile.max_health + 1, raw_after)
        if (self.self_damage_mode == 'stop_before_heal_reject_lethal'
                and raw_after <= -attacker.profile.max_health):
            raise IllegalAction('Ram self-damage at the death threshold is undecided; abort this duel')
        if (self.self_damage_mode == 'stop_before_heal_reject_lethal' and raw_after <= 0
                and attacker.profile.name != self.stop_on_attacker):
            raise IllegalAction('Ram self-incapacitation for this attacker is undecided; abort this duel')
        return raw_after

    def _ram_self_damage_mode(self):
        return self.self_damage_mode

    def _ram_scope(self):
        return 'experimental bare Ram; simultaneous damage; self-incapacity hypothesis'

    def _on_ram_opportunity(self, actor, first, second):
        super()._on_ram_opportunity(actor, first, second)
        fighter = self.fighters[actor]
        if self.self_damage_mode == 'stop_before_heal_reject_lethal' and not fighter.conscious:
            self._ram_incapacitated_actor = actor
            self._record('ram_incapacity_stop', ('ACT-05', 'DMG-05'), actor=fighter.profile.name,
                         target=second.target, trigger=self.trigger_seq, health=fighter.health,
                         reason='combat_ends_before_recovery')

    def _end_turn_effects(self, actor):
        if self._ram_incapacitated_actor == actor:
            return
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
