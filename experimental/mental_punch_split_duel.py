"""Experimental Mental Punch against the current two-check Fast Strikes host."""

from dataclasses import dataclass, replace

from blacklight.engine import Action, IllegalAction, ReactionEvent
from blacklight.pool_damage import roll_damage_pool
from combatants.split_fast import SplitFastDuel, SplitFastPolicy
from combatants.duel_adapter import REGISTRY


@dataclass(frozen=True)
class MentalPunchPolicy(SplitFastPolicy):
    prefer_mental_punch: bool = False
    shield_against_mental: bool = False

    def __post_init__(self):
        super().__post_init__()
        if type(self.prefer_mental_punch) is not bool or type(self.shield_against_mental) is not bool:
            raise ValueError('Mental Punch policy choices must be boolean')

    def choose_action(self, observation):
        if self.prefer_mental_punch and 'mental_punch' in observation.me.powers and observation.distance <= 1:
            return Action('mental_punch')
        return super().choose_action(observation)

    def use_shield_reaction(self, observation, incoming_kind):
        if incoming_kind == 'mental_punch' and not self.shield_against_mental:
            return False
        return super().use_shield_reaction(observation, incoming_kind)


class MentalPunchSplitDuel(SplitFastDuel):
    """Physical/Fast plus Mental Punch, zero Focus DR, no Karma or other controls.

    Mental users are limited to bare attacks without Mighty or Attack Stance;
    their focus damage is counted separately from Health damage metrics.
    """

    execution_scope = 'experimental_mental_punch_split_fast_duel'

    def __init__(self, *args, **kwargs):
        if kwargs.get('audit') is not True:
            raise ValueError('Mental Punch experimental duels require a full trace')
        super().__init__(*args, **kwargs)
        if self.stack_stunned_edge is not False or self.end_turn_healing_first is not True:
            raise ValueError('This host requires the documented stunned-edge and healing variants')
        if len(self.fighters) != 2 or len({f.profile.name for f in self.fighters}) != 2:
            raise ValueError('Two distinct combatants are required')
        if any(not isinstance(p, MentalPunchPolicy) for p in self.policies):
            raise ValueError('Both policies must declare mental attack preferences')
        for fighter in self.fighters:
            p = fighter.profile
            supported_powers = {key[1] for key, value in REGISTRY.items()
                                if key[0] == 'power' and value.status == 'implemented'} | {'mental_punch'}
            supported_traits = {key[1] for key, value in REGISTRY.items()
                                if key[0] == 'trait' and value.status == 'implemented'}
            supported_weapons = {'blade', 'claw', 'hammer', 'shield'}
            if (p.powers - supported_powers or p.traits - supported_traits
                    or p.weapons - supported_weapons or p.ranged_range
                    or ('shield' in p.weapons and p.rank >= 4)):
                raise ValueError('Profile includes unsupported mechanics for this experimental host')
            if 'mental_punch' in p.powers and (p.melee_bonus != 0 or p.weapons or p.ranged_range
                    or 'mighty' in p.powers or 'attack_stance' in p.powers):
                raise ValueError('Mental Punch with weapons, Mighty or Attack Stance is unsupported')

    def legal_actions(self, actor):
        actions = super().legal_actions(actor)
        if (actions and 'mental_punch' in self.fighters[actor].profile.powers and self.distance <= 1):
            actions += (Action('mental_punch'),)
        return actions

    def _attack_check_spec(self, actor, kind, target_actor=None):
        spec = super()._attack_check_spec(actor, kind, target_actor)
        return replace(spec, troubles=spec.troubles + int(self.fighters[actor].focus <= 0))

    def _act(self, actor, action):
        if isinstance(action, Action) and action.kind == 'treat_bleeding' and self.fighters[actor].focus <= 0:
            raise IllegalAction('Demoralized treatment check is not integrated in this host')
        if not isinstance(action, Action) or action.kind != 'mental_punch':
            return super()._act(actor, action)
        if action not in self.legal_actions(actor):
            raise IllegalAction('Mental Punch is unavailable')
        attacker, target_index = self.fighters[actor], self._target_index(actor)
        target = self.fighters[target_index]
        p, q = attacker.profile, target.profile
        attacker.standard_available = False
        check = self._prepare_attack_check(actor, 'melee', target_actor=target_index)
        roll = check.result
        # The explicit kind lets the defender's policy distinguish Focus damage.
        self._shield_reaction_after_check(actor, replace(check, kind='mental_punch'))
        pool = (roll_damage_pool(self.damage_rng, full_multiplier=p.rank, ability=p.melee,
                                 reduction=0, fantastic=roll.fantastic)
                if roll.success else None)
        damage = pool.damage if pool else 0
        before = target.focus
        after = before - damage
        if p.heroic and after <= -q.max_focus:
            after = -q.max_focus + 1
        target.focus = after
        attacker.attacks += 1
        attacker.hits += int(roll.success)
        attacker.fantastic_hits += int(roll.success and roll.fantastic)
        self._record('mental_attack', ('CORE-P108-MENTAL-PUNCH', 'DMG-05'), actor=p.name, target=q.name,
            trigger=check.trigger, distance=self.distance, roll=[roll.roll.left, roll.roll.marvel, roll.roll.right],
            rerolls=[vars(item) for item in check.rerolls], modifier=check.spec.modifier,
            target_number=check.spec.target, edges=check.spec.edges, troubles=check.spec.troubles,
            total=roll.total, success=roll.success, fantastic=roll.fantastic, ultimate=roll.ultimate,
            focus_before=before, focus_after=after, damage=before - after, calculated_damage=damage,
            damage_faces=list(pool.faces) if pool else [], focus_reduction=0,
            demoralized=after <= 0, shattered=after <= -q.max_focus)
        if roll.success and roll.fantastic and after > -q.max_focus:
            attacker.stuns_applied += 1
            target.stunned_by = actor
            target.stun_expires_on_actor_turn = self.turn_counts[actor] + 1
            target.stance = False
            self._record('condition_start', ('CORE-P108-MENTAL-PUNCH', 'COND-02'),
                         actor=q.name, condition='stunned', expires_on_actor=p.name,
                         source_turn_count=target.stun_expires_on_actor_turn)
        if not roll.success:
            self._queue_reaction(ReactionEvent('riposte', target_index, actor, check.trigger))
            self._record('reaction_queued', ('ACT-03', 'POW-06'), actor=q.name,
                         trigger=check.trigger, source=p.name)
        self._drain_events()

    def _outcome(self):
        active = [f.conscious and f.focus > -f.profile.max_focus for f in self.fighters]
        if all(active):
            return None
        if not any(active):
            return 'draw', None
        return 'win', self.fighters[active.index(True)].profile.name
