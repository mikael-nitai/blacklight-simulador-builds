"""Resolve one bare Ram at a real duel opportunity, then stop the experiment."""

from dataclasses import asdict

from blacklight.engine import IllegalAction
from .ram_opportunity_duel import RamOpportunityDuel
from .ram_record import record_table_ram
from .ram_rolled import audit_rolled_table_ram
from .ram_transaction import RamState


class _RamCheckpointReached(Exception):
    pass


_SUPPORTED_POWERS = frozenset({'healing_factor', 'brawling', 'fast_strikes', 'attack_stance',
                               'riposte', 'do_this_all_day', 'blazing_fast_fists',
                               'mighty', 'sturdy', 'accuracy'})
_SUPPORTED_TRAITS = frozenset({'battle_ready', 'combat_reflexes', 'situational_awareness',
                               'signature_fast_strikes'})
_SUPPORTED_WEAPONS = frozenset({'blade', 'claw', 'hammer', 'shield'})


class RamCheckpointDuel(RamOpportunityDuel):
    """Stop at one selected actor's first opportunity; never claim a full duel."""

    execution_scope = 'experimental_ram_checkpoint_only'

    def __init__(self, *args, ram_actor, **kwargs):
        if type(ram_actor) is not int or ram_actor not in (0, 1):
            raise ValueError('Select exactly one Ram actor')
        if kwargs.get('audit') is not True:
            raise ValueError('Experimental Ram checkpoints require a complete trace')
        super().__init__(*args, **kwargs)
        if len(self.fighters) != 2 or self.fighters[0].profile.name == self.fighters[1].profile.name:
            raise ValueError('Experimental Ram checkpoint requires two distinct combatants')
        if any(f.profile.powers - _SUPPORTED_POWERS or f.profile.traits - _SUPPORTED_TRAITS
               or f.profile.weapons - _SUPPORTED_WEAPONS for f in self.fighters):
            raise ValueError('A profile contains mechanics unsupported by this checkpoint')
        self.ram_actor = ram_actor
        self._checkpoint = None
        self._probe_started = False
        self._probe_closed = False

    def _on_ram_opportunity(self, actor, first, second):
        if actor == self.ram_actor:
            self._checkpoint = (actor, first, second, self._snapshot())
            raise _RamCheckpointReached()

    def _snapshot(self):
        return (self.distance, tuple((f.profile, f.health, f.focus, f.reactions, f.shield_active,
                                     f.stance, f.stunned_by, f.dodging, f.bleeding)
                                    for f in self.fighters), tuple(self.policies),
                self.rng.getstate(), self.damage_rng.getstate())

    def run_to_opportunity(self):
        if self._probe_started:
            raise IllegalAction('This checkpoint can only be run once')
        self._probe_started = True
        try:
            outcome = super().run()
        except _RamCheckpointReached:
            return {'status': 'opportunity', 'log': tuple(self.log)}
        self._probe_closed = True
        return {'status': 'no_opportunity', 'outcome': outcome, 'log': tuple(self.log)}

    def run(self):
        raise IllegalAction('Use run_to_opportunity; this checkpoint cannot run a full Ram duel')

    def resolve_bare_ram(self):
        """Resolve once, without continuing combat or modeling unsupported reactions."""
        if self._checkpoint is None or self._probe_closed:
            raise IllegalAction('No open Ram checkpoint')
        self._probe_closed = True
        actor, first, second, snapshot = self._checkpoint
        if self._snapshot() != snapshot:
            raise IllegalAction('Combat state changed after the Ram checkpoint')
        target_actor = self._target_index(actor)
        attacker, target = self.fighters[actor], self.fighters[target_actor]
        p, q = attacker.profile, target.profile
        if any(profile.powers - _SUPPORTED_POWERS or profile.traits - _SUPPORTED_TRAITS
               or profile.weapons - _SUPPORTED_WEAPONS for profile in (p, q)):
            raise IllegalAction('A profile contains mechanics unsupported by this checkpoint')
        if (attacker.shield_active or target.shield_active
                or 'shield' in q.weapons and target.reactions > 0
                or 'riposte' in q.powers and target.reactions > 0
                or attacker.stance or target.dodging or target.stunned_by is not None):
            raise IllegalAction('Shield, Riposte, stance, Dodge or Stunned interaction is not supported by this checkpoint')
        before = RamState(attacker.health, target.health, attacker.reactions,
                          attacker.conscious and attacker.stunned_by is None, False)
        spec = self._attack_check_spec(actor, 'melee', target_actor)
        check = self._prepare_attack_check(actor, 'melee', spec, target_actor=target_actor)
        hit = check.result
        if (hit.success and hit.fantastic and 'mighty' in p.powers
                and self.policies[actor].choose_knockback(self.observe(actor, target_actor), 'melee')):
            raise IllegalAction('Selected Mighty knockback is not supported by this checkpoint')
        full_dice = p.rank + max(0, p.melee_bonus)
        if hit.success:
            target_faces = tuple(self.damage_rng.randint(1, 6) for _ in range(full_dice))
            attacker_faces = tuple(self.damage_rng.randint(1, 6) for _ in range(full_dice))
        else:
            target_faces = attacker_faces = ()
        record = record_table_ram(before, first, second, success=hit.success,
                                  fantastic_success=hit.success and hit.fantastic,
                                  full_dice=full_dice, ability=p.melee,
                                  target_reduction=q.health_dr, attacker_reduction=p.health_dr,
                                  target_faces=target_faces, attacker_faces=attacker_faces)
        record['check'] = {'seed': self.seed,
                           'roll': [hit.roll.left, hit.roll.marvel, hit.roll.right],
                           'rerolls': [asdict(item) for item in check.rerolls],
                           'modifier': spec.modifier, 'target_number': spec.target,
                           'edges': spec.edges, 'troubles': spec.troubles,
                           'total': hit.total, 'success': hit.success,
                           'fantastic_roll': hit.fantastic, 'ultimate': hit.ultimate}
        issues = audit_rolled_table_ram(record)
        if issues:
            raise RuntimeError(f'Ram checkpoint audit failed: {issues}')
        if p.heroic and record['after']['target_health'] <= -q.max_health:
            raise IllegalAction('Heroic damage floor interaction is not supported by this checkpoint')
        # The checkpoint stops immediately after this atomic hypothetical event.
        attacker.reactions = record['after']['reactions']
        attacker.health = record['after']['attacker_health']
        target.health = record['after']['target_health']
        self._record('ram_checkpoint_resolved', ('ACT-01', 'ACT-03'),
                     actor=p.name, target=q.name, transaction=record,
                     scope='experimental bare Ram; combat stops immediately')
        return {'status': 'resolved_checkpoint', 'transaction': record, 'log': tuple(self.log)}
