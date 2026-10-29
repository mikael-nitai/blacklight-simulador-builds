"""Experimental two-person open-field duel with the Prone condition."""

from dataclasses import dataclass, replace

from blacklight.engine import Action, IllegalAction, Move, Observation
from combatants.duel_adapter import REGISTRY
from combatants.split_fast import SplitFastDuel, SplitFastPolicy
from .prone import attack_modifiers


@dataclass(frozen=True)
class ProneObservation(Observation):
    me_prone: bool = False
    foe_prone: bool = False


@dataclass(frozen=True)
class PronePolicy(SplitFastPolicy):
    """Explicitly decide whether to use one space of movement to stand."""

    stand_when_prone: bool = True

    def __post_init__(self):
        super().__post_init__()
        if type(self.stand_when_prone) is not bool:
            raise ValueError('Standing preference must be boolean')

    def choose_prone_stand(self, observation, *, as_standard):
        return self.stand_when_prone and observation.me.run_speed > 0

    def _prone_move(self, observation, move):
        if move is None or not observation.me_prone:
            return move
        capacity = max(0, observation.me.run_speed - 1) if self.stand_when_prone else 0
        return Move(move.direction if capacity else 'stay', min(move.steps, capacity))

    def choose_move(self, observation):
        return self._prone_move(observation, super().choose_move(observation))

    def choose_post_move(self, observation):
        return self._prone_move(observation, super().choose_post_move(observation))

    def choose_action(self, observation):
        action = super().choose_action(observation)
        if observation.me_prone and action.kind == 'move' and action.move is not None:
            if not self.stand_when_prone or observation.me.run_speed == 0:
                return Action('wait')
            return replace(action, move=self._prone_move(observation, action.move))
        return action


class ProneDuel(SplitFastDuel):
    """A deliberately limited host; no crawling or Ram is implemented."""

    execution_scope = 'experimental_prone_duel'
    additional_experimental_powers = frozenset()

    def __init__(self, *args, initial_prone=(False, False), **kwargs):
        if (not isinstance(initial_prone, tuple) or len(initial_prone) != 2
                or any(type(value) is not bool for value in initial_prone)):
            raise ValueError('Declare exactly two initial Prone flags')
        if kwargs.get('audit') is not True:
            raise ValueError('Experimental Prone duels require a complete trace')
        super().__init__(*args, **kwargs)
        if (len(self.fighters) != 2 or len(self.policies) != 2
                or self.fighters[0].profile.name == self.fighters[1].profile.name):
            raise ValueError('Experimental Prone duel requires two distinct combatants')
        allowed = {kind: {identity for (family, identity), entry in REGISTRY.items()
                          if family == kind and entry.status == 'implemented'}
                   for kind in ('power', 'trait', 'house_weapon')}
        allowed['power'].update(self.additional_experimental_powers)
        for fighter, policy in zip(self.fighters, self.policies):
            p = fighter.profile
            if (p.powers - allowed['power'] or p.traits - allowed['trait']
                    or p.weapons - allowed['house_weapon']
                    or 'fast_strikes' in p.powers and p.melee % 2
                    or 'shield' in p.weapons and p.rank >= 4):
                raise ValueError('A profile contains mechanics unsupported by this Prone duel')
            if not callable(getattr(policy, 'choose_prone_stand', None)):
                raise ValueError('Both policies must explicitly decide whether to stand')
        self.prone = list(initial_prone)
        for actor, flag in enumerate(initial_prone):
            if flag:
                self._record('prone_initial', ('ACT-06',), actor=self.fighters[actor].profile.name)

    def observe(self, actor, target_actor=None):
        target = self._target_index(actor, target_actor)
        base = super().observe(actor, target)
        return ProneObservation(base.me, base.foe, base.distance, base.round,
                                base.bonus_round, base.terrain, self.prone[actor], self.prone[target])

    def _attack_check_spec(self, actor, kind, target_actor=None):
        target = self._target_index(actor, target_actor)
        spec = super()._attack_check_spec(actor, kind, target)
        ranged = kind == 'ranged'
        modifiers = attack_modifiers(attacker_prone=self.prone[actor], target_prone=self.prone[target],
                                     ability='agility' if ranged else 'melee',
                                     attack_range='ranged' if ranged else 'close')
        return replace(spec, edges=spec.edges + modifiers.edges,
                       troubles=spec.troubles + modifiers.troubles)

    def _prepare_attack_check(self, actor, kind, spec=None, *, target_actor=None):
        target = self._target_index(actor, target_actor)
        if spec is None:
            spec = self._attack_check_spec(actor, kind, target)
        if self.prone[actor] or self.prone[target]:
            ranged = kind == 'ranged'
            modifiers = attack_modifiers(attacker_prone=self.prone[actor], target_prone=self.prone[target],
                                         ability='agility' if ranged else 'melee',
                                         attack_range='ranged' if ranged else 'close')
            self._record('prone_check', ('ACT-05',), actor=self.fighters[actor].profile.name,
                         target=self.fighters[target].profile.name, mode=kind, trigger=self.trigger_seq + 1,
                         attacker_prone=self.prone[actor], target_prone=self.prone[target],
                         added_edges=modifiers.edges, added_troubles=modifiers.troubles)
        return super()._prepare_attack_check(actor, kind, spec, target_actor=target)

    def _move(self, actor, move, *, as_standard=False):
        if (type(actor) is not int or not 0 <= actor < len(self.fighters)
                or not isinstance(move, Move) or type(move.steps) is not int
                or type(as_standard) is not bool):
            raise IllegalAction('Movement requires a valid actor and integer grid steps')
        if not self.prone[actor]:
            return super()._move(actor, move, as_standard=as_standard)
        fighter = self.fighters[actor]
        if (self.active_actor != actor or not fighter.conscious or fighter.stunned_by is not None
                or as_standard and not fighter.standard_available
                or not as_standard and not fighter.movement_available
                or move.direction not in ('stay', 'approach', 'retreat')
                or not 0 <= move.steps <= fighter.profile.run_speed
                or move.direction == 'stay' and move.steps != 0):
            raise IllegalAction('Invalid Prone movement request')
        wants = self.policies[actor].choose_prone_stand(self.observe(actor), as_standard=as_standard)
        if type(wants) is not bool:
            raise IllegalAction('Standing decision must be boolean')
        if not wants:
            if move.steps:
                raise IllegalAction('Moving while Prone is unsupported in this host')
            return super()._move(actor, move, as_standard=as_standard)
        if fighter.profile.run_speed < 1 or move.steps + 1 > fighter.profile.run_speed:
            raise IllegalAction('Standing plus movement exceeds the movement budget')
        self.prone[actor] = False
        self._record('prone_stand', ('ACT-06',), actor=fighter.profile.name,
                     cost=1, as_standard=as_standard, speed=fighter.profile.run_speed)
        return super()._move(actor, move, as_standard=as_standard)
