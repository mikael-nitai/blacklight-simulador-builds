"""Riposte and Point-Blank Parry during a two-person hold."""

from dataclasses import dataclass, replace

from blacklight.engine import IllegalAction
from .entangled_attack_duel import EntangledAttackDuel, EntangledAttackPolicy
from .grappling_duel import GrapplingPolicy


@dataclass(frozen=True)
class EntangledReactionPolicy(EntangledAttackPolicy):
    use_entangled_reactions: bool = True

    def __post_init__(self):
        super().__post_init__()
        if type(self.use_entangled_reactions) is not bool:
            raise ValueError('Entangled reaction preference must be boolean')

    def choose_miss_reaction(self, observation, options):
        if ((observation.me_grabbed or observation.me_grabbing) and not self.use_entangled_reactions):
            return None
        return super(GrapplingPolicy, self).choose_miss_reaction(observation, options)


class EntangledReactionDuel(EntangledAttackDuel):
    """Allow only the inherited miss reactions; nested reactions interrupt the queue."""

    execution_scope = 'experimental_entangled_reaction_duel'

    def __init__(self, *args, **kwargs):
        self._draining_entangled_reactions = False
        super().__init__(*args, **kwargs)
        if any(not isinstance(policy, EntangledReactionPolicy) for policy in self.policies):
            raise ValueError('Both policies must declare entangled reaction choices')

    def _reaction_source_available(self, event):
        return self.fighters[event.source].conscious and super()._reaction_source_available(event)

    def _queue_reaction(self, event):
        super()._queue_reaction(event)
        if self._draining_entangled_reactions:
            if not self.pending or self.pending[-1] is not event:
                raise RuntimeError('Nested reaction was not queued as expected')
            self.pending.rotate(1)

    def _reaction_dequeued(self, event):
        super()._reaction_dequeued(event)
        self._record('entangled_reaction_dequeued', ('ACT-03',),
            actor=self.fighters[event.reactor].profile.name,
            source=self.fighters[event.source].profile.name,
            trigger=event.trigger, reaction_kind=event.kind)

    def _drain_events(self):
        if self._draining_entangled_reactions:
            raise RuntimeError('Unexpected nested queue drain')
        self._draining_entangled_reactions = True
        try:
            return super()._drain_events()
        finally:
            self._draining_entangled_reactions = False

    def _attack(self, actor, kind, *, reaction=False, offhand=None, fast_strike=None,
                prepared_check=None, target_actor=None):
        if self.holder is not None and kind == 'ranged':
            last = self.log[-1] if self.log else {}
            if (not self._draining_entangled_reactions or last.get('type') != 'parry_start'
                    or last.get('actor') != self.fighters[actor].profile.name):
                raise IllegalAction('Only Point-Blank Parry permits a ranged attack during a hold')
        return super()._attack(actor, kind, reaction=reaction, offhand=offhand,
                               fast_strike=fast_strike, prepared_check=prepared_check,
                               target_actor=target_actor)

    def _attack_check_spec(self, actor, kind, target_actor=None):
        if self.holder is None or kind != 'ranged':
            return super()._attack_check_spec(actor, kind, target_actor)
        spec = super(EntangledAttackDuel, self)._attack_check_spec(actor, kind, target_actor)
        pinned = actor != self.holder and self.pinned_target
        return replace(spec, troubles=spec.troubles + int(pinned) + int(self.inside_attack_trouble))

    def _prepare_attack_check(self, actor, kind, spec=None, *, target_actor=None):
        if self.holder is None or kind != 'ranged':
            return super()._prepare_attack_check(actor, kind, spec, target_actor=target_actor)
        target = self._target_index(actor, target_actor)
        pinned = actor != self.holder and self.pinned_target
        self._record('entangled_attack_check', ('CORE-P30-GRAB',),
            actor=self.fighters[actor].profile.name, target=self.fighters[target].profile.name,
            mode=kind, trigger=self.trigger_seq + 1, pinned=pinned,
            inside_attack_trouble=self.inside_attack_trouble,
            added_troubles=int(pinned) + int(self.inside_attack_trouble))
        return super(EntangledAttackDuel, self)._prepare_attack_check(actor, kind, spec,
                                                                     target_actor=target_actor)
