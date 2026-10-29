"""Restricted experimental duel host for the Slow-Motion Dodge contract.

This host deliberately excludes biological weapons, Fast, other powers and
non-Heroic profiles until their interactions have their own auditing.
"""

from dataclasses import dataclass, replace

from blacklight.engine import IllegalAction
from combatants.split_fast import SplitFastDuel, SplitFastPolicy
from .slow_motion_dodge import DodgeTrigger, can_use_slow_motion_dodge, resolve_slow_motion_dodge


@dataclass(frozen=True)
class SlowMotionPolicy(SplitFastPolicy):
    dodge_agility_attacks: bool = True

    def __post_init__(self):
        super().__post_init__()
        if type(self.dodge_agility_attacks) is not bool:
            raise ValueError('Slow-Motion Dodge preference must be boolean')

    def choose_slow_motion_dodge(self, observation):
        return self.dodge_agility_attacks


class SlowMotionAttackMixin:
    """Apply the verified power before a host resolves its ranged attack."""
    def _attack(self, actor, kind, *, reaction=False, offhand=None, fast_strike=None,
                prepared_check=None, target_actor=None):
        if kind != 'ranged' or prepared_check is not None:
            return super()._attack(actor, kind, reaction=reaction, offhand=offhand,
                                   fast_strike=fast_strike, prepared_check=prepared_check,
                                   target_actor=target_actor)
        if reaction or offhand is not None or fast_strike is not None:
            raise IllegalAction('Unsupported ranged reaction or attack combination')
        target = self._target_index(actor, target_actor)
        defender = self.fighters[target]
        profile = defender.profile
        spec = self._attack_check_spec(actor, kind, target)
        trigger_id = self.trigger_seq + 1
        context = DodgeTrigger('slow_motion_dodge' in profile.powers, True,
                               'melee' if 'brawling' in profile.powers else 'agility',
                               True, defender.conscious and defender.stunned_by is None,
                               defender.reactions, trigger_id in defender.reacted_to)
        decision = False
        if can_use_slow_motion_dodge(context):
            decision = self.policies[target].choose_slow_motion_dodge(self.observe(target, actor))
            if type(decision) is not bool:
                raise IllegalAction('Slow-Motion Dodge decision must be boolean')
        result = resolve_slow_motion_dodge(context, activate=decision)
        if result.activated:
            defender.reactions = result.reactions_remaining
            defender.reacted_to.add(trigger_id)
            spec = replace(spec, troubles=spec.troubles + result.added_troubles)
            self._record('reaction_spent', ('ACT-03', 'ACT-04', 'SLOW-MOTION-DODGE'),
                         actor=profile.name, trigger=trigger_id, remaining=defender.reactions,
                         source='slow_motion_dodge')
            self._record('slow_motion_dodge', ('SLOW-MOTION-DODGE',), actor=profile.name,
                         attacker=self.fighters[actor].profile.name, trigger=trigger_id,
                         added_troubles=result.added_troubles, before_roll=True)
        check = self._prepare_attack_check(actor, kind, spec, target_actor=target)
        return super()._attack(actor, kind, reaction=False, prepared_check=check,
                               target_actor=target)


class SlowMotionDuel(SlowMotionAttackMixin, SplitFastDuel):
    execution_scope = 'experimental_slow_motion_restricted_duel'

    def __init__(self, *args, **kwargs):
        if kwargs.get('audit') is not True:
            raise ValueError('Slow-Motion Dodge requires a complete trace')
        super().__init__(*args, **kwargs)
        if len(self.fighters) != 2 or len(self.policies) != 2:
            raise ValueError('Exactly two fighters and policies are required')
        if self.fighters[0].profile.name == self.fighters[1].profile.name:
            raise ValueError('Combatant names must be distinct')
        for fighter, policy in zip(self.fighters, self.policies):
            p = fighter.profile
            if (p.powers - {'slow_motion_dodge', 'accuracy', 'brawling'}
                    or p.traits - {'combat_reflexes'} or p.weapons or not p.heroic):
                raise ValueError('Profile is outside the experimental Slow-Motion scope')
            if not callable(getattr(policy, 'choose_slow_motion_dodge', None)):
                raise ValueError('Each policy must explicitly decide whether to dodge')
