"""Experimental one-dimensional duel combining bare Ram with Prone."""

from dataclasses import asdict, dataclass

from blacklight.engine import IllegalAction, ReactionEvent
from .prone_duel import ProneDuel, PronePolicy
from .ram_opportunity_duel import RamOpportunityDuel
from .ram_record import record_table_ram
from .ram_rolled import audit_rolled_table_ram
from .ram_transaction import RamState


@dataclass(frozen=True)
class RamPronePolicy(PronePolicy):
    """Use bare Ram when available; retain an active Shield instead of attacking."""

    use_ram: bool = True

    def __post_init__(self):
        super().__post_init__()
        if type(self.use_ram) is not bool:
            raise ValueError('Ram choice must be boolean')

    def choose_ram(self, observation):
        return self.use_ram and not observation.me.shield_active


class RamProneDuel(RamOpportunityDuel, ProneDuel):
    """Bare Ram only, with conservative guards against unresolved interactions."""

    execution_scope = 'experimental_ram_prone_duel'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if any(not callable(getattr(policy, 'choose_ram', None)) for policy in self.policies):
            raise ValueError('Both policies must explicitly decide whether to use Ram')

    def _on_ram_opportunity(self, actor, first, second):
        choice = self.policies[actor].choose_ram(self.observe(actor))
        if type(choice) is not bool:
            raise IllegalAction('Ram choice must be boolean')
        if not choice:
            self._record('ram_declined', ('ACT-03',), actor=self.fighters[actor].profile.name,
                         target=second.target)
            return
        attacker = self.fighters[actor]
        target_actor = self._target_index(actor)
        target = self.fighters[target_actor]
        p, q = attacker.profile, target.profile
        if attacker.shield_active or attacker.stance:
            raise IllegalAction('Ram with an active attacker Shield or Attack Stance is unsupported')
        before = RamState(attacker.health, target.health, attacker.reactions,
                          attacker.conscious and attacker.stunned_by is None, self.prone[target_actor])
        attacker.reactions -= 1
        self._record('reaction_spent', ('ACT-03',), actor=p.name, source='ram',
                     remaining=attacker.reactions)
        spec = self._attack_check_spec(actor, 'melee', target_actor)
        check = self._prepare_attack_check(actor, 'melee', spec, target_actor=target_actor)
        hit = check.result
        self._shield_reaction_after_check(actor, check)
        target_reduction = q.health_dr + (2 if target.shield_active else 0)
        full_dice = p.rank + max(0, p.melee_bonus)
        if hit.success:
            target_faces = tuple(self.damage_rng.randint(1, 6) for _ in range(full_dice))
            attacker_faces = tuple(self.damage_rng.randint(1, 6) for _ in range(full_dice))
        else:
            target_faces = attacker_faces = ()
        record = record_table_ram(before, first, second, success=hit.success,
                                  fantastic_success=hit.success and hit.fantastic,
                                  full_dice=full_dice, ability=p.melee,
                                  target_reduction=target_reduction, attacker_reduction=p.health_dr,
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
            raise RuntimeError(f'Ram transaction failed audit: {issues}')
        if record['after']['attacker_health'] <= 0:
            raise IllegalAction('Ram self-incapacitation timing is unresolved; abort this experimental duel')
        raw_target_health = record['after']['target_health']
        target_after = max(-q.max_health + 1, raw_target_health) if p.heroic else raw_target_health
        applied_target = target.health - target_after
        self_damage = record['impact']['attacker_damage']
        multiplier = 3 if hit.success and hit.fantastic else 2
        raw_regular = (max(0, sum(6 if face == 1 else face for face in target_faces) + p.melee)
                       if hit.success and full_dice > 0 else 0)
        mitigation = max(0, raw_regular * multiplier - record['impact']['target_damage'])
        attacker.attacks += 1
        if hit.success:
            attacker.hits += 1
            attacker.fantastic_hits += int(hit.fantastic)
        attacker.damage_dealt += applied_target
        attacker.damage_taken += self_damage
        target.damage_taken += applied_target
        target.damage_mitigated += mitigation
        attacker.health = record['after']['attacker_health']
        target.health = target_after
        if not target.conscious:
            target.stance = False
        self._record('ram_attack', ('ACT-01', 'ACT-03', 'ACT-05'), actor=p.name, target=q.name,
                     trigger=check.trigger, mode='melee', edges=spec.edges, troubles=spec.troubles,
                     transaction=record, target_health_after=target_after,
                     target_damage_applied=applied_target, attacker_damage_applied=self_damage,
                     target_damage_mitigated=mitigation,
                     scope='experimental bare Ram; simultaneous damage; no self-incapacitation')
        if hit.success and hit.fantastic and not self.prone[target_actor]:
            self.prone[target_actor] = True
            self._record('prone_start', ('ACT-05',), actor=q.name, source=p.name, trigger=check.trigger)
        if not hit.success:
            self._queue_reaction(ReactionEvent('riposte', target_actor, actor, check.trigger))
            self._record('reaction_queued', ('ACT-03', 'POW-06'), actor=q.name,
                         trigger=check.trigger, source=p.name)
            self._drain_events()
