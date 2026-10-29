"""Experimental attacks between participants of a two-person hold."""

from dataclasses import dataclass, replace

from blacklight.engine import Action, IllegalAction
from combatants.split_fast import ATTACK_KINDS
from .grappling_duel import GrapplingDuel, GrapplingPolicy


@dataclass(frozen=True)
class EntangledAttackPolicy(GrapplingPolicy):
    attack_when_grabbed: bool = False
    attack_when_grabbing: bool = False

    def __post_init__(self):
        super().__post_init__()
        if type(self.attack_when_grabbed) is not bool or type(self.attack_when_grabbing) is not bool:
            raise ValueError('Entangled attack preferences must be boolean')

    def choose_action(self, observation):
        wants_attack = ((observation.me_grabbed and self.attack_when_grabbed)
                        or (observation.me_grabbing and self.attack_when_grabbing))
        if not wants_attack:
            return super().choose_action(observation)
        if self.weapon in ('blade', 'claw', 'hammer'):
            kind = self.weapon + ('_fast' if self.prefer_fast else '')
        else:
            kind = 'fast_strikes' if self.prefer_fast and 'fast_strikes' in observation.me.powers else 'melee'
        return self._select_effects(Action(kind, offhand=self.offhand if self.prefer_fast else None))

    def choose_knockback(self, observation, mode):
        if observation.me_grabbed or observation.me_grabbing:
            return False
        return super().choose_knockback(observation, mode)


class EntangledAttackDuel(GrapplingDuel):
    """Require a declared inside-attack trouble interpretation.

    Self-hit on a miss, reactions against attacks while held, attacks on third
    parties and knockback during a hold remain outside the experiment.
    """

    execution_scope = 'experimental_entangled_attack_duel'

    def __init__(self, *args, inside_attack_trouble, **kwargs):
        if type(inside_attack_trouble) is not bool:
            raise ValueError('Declare the inside-attack trouble hypothesis')
        self.inside_attack_trouble = inside_attack_trouble
        super().__init__(*args, **kwargs)
        if any(not isinstance(policy, EntangledAttackPolicy) for policy in self.policies):
            raise ValueError('Both policies must handle entangled attack choices')

    def legal_actions(self, actor):
        if self.holder is None:
            return super().legal_actions(actor)
        prior = super(GrapplingDuel, self).legal_actions(actor)
        if not prior:
            return ()
        attacks = tuple(action for action in prior if action.kind in ATTACK_KINDS and action.kind != 'ranged')
        return attacks + ((Action('wait'), Action('release_hold')) if actor == self.holder
                          else (Action('wait'), Action('escape')))

    def _act(self, actor, action):
        if self.holder is not None and isinstance(action, Action) and action.kind in ATTACK_KINDS:
            if action.kind == 'ranged' or action not in self.legal_actions(actor):
                raise IllegalAction('Unsupported attack while entangled')
            return super(GrapplingDuel, self)._act(actor, action)
        return super()._act(actor, action)

    def _attack_check_spec(self, actor, kind, target_actor=None):
        spec = super()._attack_check_spec(actor, kind, target_actor)
        if self.holder is None:
            return spec
        target = self._target_index(actor, target_actor)
        if target == actor or kind == 'ranged':
            raise IllegalAction('Unsupported entangled attack target or mode')
        pinned = actor != self.holder and self.pinned_target
        return replace(spec, troubles=spec.troubles + int(pinned) + int(self.inside_attack_trouble))

    def _prepare_attack_check(self, actor, kind, spec=None, *, target_actor=None):
        if self.holder is not None:
            target = self._target_index(actor, target_actor)
            self._record('entangled_attack_check', ('CORE-P30-GRAB',),
                actor=self.fighters[actor].profile.name, target=self.fighters[target].profile.name,
                mode=kind, trigger=self.trigger_seq + 1, pinned=actor != self.holder and self.pinned_target,
                inside_attack_trouble=self.inside_attack_trouble,
                added_troubles=int(actor != self.holder and self.pinned_target) + int(self.inside_attack_trouble))
        return super()._prepare_attack_check(actor, kind, spec, target_actor=target_actor)

    def _validate_knockback(self, actor, spaces):
        if self.holder is not None and spaces:
            raise IllegalAction('Knockback during an active hold is unsupported')
        return super()._validate_knockback(actor, spaces)
