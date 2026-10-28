"""Current physical combat for arbitrary rosters at fixed mutual contact.

Attack rolls, damage, standard modules and reaction resolution are inherited;
this host supplies teams, target declarations and scheduled inactive turns.
It does not claim to implement positioning, resurrection or Karma recovery.
This migration is experimental: the current tests cover selected fixed-contact
cases, not a complete group-combat or independent rules certification.
"""

from dataclasses import dataclass, replace
from itertools import product

from blacklight.engine import Action, FighterView, IllegalAction, Move, Observation
from .lifecycle import Boundary, TimePoint, TimedEffect, expiration_plan
from .split_fast import ATTACK_KINDS, FastAction, SplitFastDuel, SplitFastPolicy, is_fast


@dataclass(frozen=True)
class TargetAction(Action):
    target_actor: int | None = None

    def __post_init__(self):
        if (self.kind not in ATTACK_KINDS or is_fast(self.kind)
                or type(self.target_actor) is not int or self.target_actor < 0
                or type(self.focus) is not int or self.focus != 0
                or self.move is not None or self.offhand is not None):
            raise ValueError('One ordinary attack requires one predeclared target')


@dataclass(frozen=True)
class GroupObservation(Observation):
    actor: int = 0
    focus_target: int = 1
    fighters: tuple[FighterView, ...] = ()
    teams: tuple[str, ...] = ()

    @property
    def enemies(self) -> tuple[int, ...]:
        return tuple(i for i, fighter in enumerate(self.fighters)
                     if self.teams[i] != self.teams[self.actor] and fighter.health > 0)


@dataclass(frozen=True)
class GroupPolicy(SplitFastPolicy):
    split_targets: bool = False
    target_order: str = 'lowest_health'
    knockback_stance: bool = False

    def __post_init__(self):
        super().__post_init__()
        if (type(self.split_targets) is not bool
                or self.target_order not in ('lowest_health', 'highest_health', 'lowest_defense')
                or self.kite or self.move_after_attack or self.knockback_stance):
            raise ValueError('Fixed-contact group policy cannot move or select knockback')

    def choose_move(self, observation):
        return Move()

    def choose_post_move(self, observation):
        return Move()

    def _targeted(self, action: Action, observation: GroupObservation) -> Action:
        if action.kind not in ATTACK_KINDS:
            return action
        def key(index):
            fighter = observation.fighters[index]
            value = (fighter.melee_defense if self.target_order == 'lowest_defense' else
                     -fighter.health if self.target_order == 'highest_health' else fighter.health)
            return value, index
        enemies = sorted(observation.enemies, key=key)
        if not enemies:
            return Action('wait')
        if is_fast(action.kind):
            second = enemies[1] if self.split_targets and len(enemies) > 1 else enemies[0]
            return replace(action, targets=(enemies[0], second))
        return TargetAction(action.kind, target_actor=enemies[0])

    def choose_action(self, observation):
        return self._targeted(super().choose_action(observation), observation)

    def choose_blade_bonus(self, observation):
        return self._targeted(super().choose_blade_bonus(observation), observation)


@dataclass(frozen=True)
class GroupResult:
    seed: int
    winner: str | None
    outcome: str
    rounds: int
    turns: int
    bonus_round_occurred: bool
    teams: tuple[str, ...]
    final_health: tuple[int, ...]
    final_focus: tuple[int, ...]
    metrics: tuple[dict, ...]
    log: tuple[dict, ...]
    initiative_roles: tuple[str, ...] | None = None
    initiative_tie_order: tuple[int, ...] | None = None
    initiative_order: tuple[int, ...] | None = None
    evidence_scope: str = 'experimental_group_uncertified'


class GroupBattle(SplitFastDuel):
    execution_scope = 'experimental_group'

    def __init__(self, profiles, policies, *, teams: tuple[str, ...],
                 initiative_roles: tuple[str, ...] | None = None,
                 initiative_tie_order: tuple[int, ...] | None = None, **kwargs):
        if (not isinstance(profiles, tuple) or len(profiles) < 2
                or not isinstance(policies, tuple) or len(policies) != len(profiles)
                or not isinstance(teams, tuple) or len(teams) != len(profiles)
                or any(not isinstance(team, str) or not team.strip() for team in teams)
                or len(set(teams)) < 2
                or len({profile.name for profile in profiles}) != len(profiles)
                or kwargs.get('initial_distance', 1) != 1):
            raise ValueError('A group requires distinct names, policies and at least two teams at contact')
        count = len(profiles)
        if (initiative_roles is not None and
                (not isinstance(initiative_roles, tuple) or len(initiative_roles) != count
                 or any(role not in ('player', 'npc') for role in initiative_roles))):
            raise ValueError('Declare player or npc for every combatant')
        if (initiative_tie_order is not None and
                (not isinstance(initiative_tie_order, tuple) or len(initiative_tie_order) != count
                 or any(type(index) is not int for index in initiative_tie_order)
                 or set(initiative_tie_order) != set(range(count)))):
            raise ValueError('Tie order must be a permutation of roster indices')
        super().__init__(profiles, policies, **kwargs)
        self.teams = teams
        self.initiative_roles = initiative_roles
        self.initiative_tie_order = initiative_tie_order
        self.resolved_initiative_order = None
        self._timed_stuns: tuple[TimedEffect, ...] = ()

    def _initiative(self):
        if self.initiative_roles is None:
            raise ValueError('Group initiative needs explicit player/npc roles')
        return super()._initiative()

    def _initiative_order(self, checks, modifiers):
        keys = [(-check.total, -int(check.fantastic), -modifiers[i],
                 0 if self.initiative_roles[i] == 'player' else 1)
                for i, check in enumerate(checks)]
        if len(set(keys)) != len(keys) and self.initiative_tie_order is None:
            raise ValueError('Remaining initiative tie needs an explicit agreed tie order')
        order = self.initiative_tie_order or tuple(range(len(checks)))
        priority = {actor: position for position, actor in enumerate(order)}
        result = tuple(sorted(range(len(checks)), key=lambda i: (keys[i], priority[i])))
        self.resolved_initiative_order = result
        self._record('group_initiative_order', ('ACT-02',),
                     roles=list(self.initiative_roles),
                     tie_order=list(self.initiative_tie_order) if self.initiative_tie_order else None,
                     order=list(result))
        return result

    def _enemies(self, actor, *, conscious=True):
        return tuple(i for i, fighter in enumerate(self.fighters)
                     if self.teams[i] != self.teams[actor] and (fighter.conscious or not conscious))

    def _target_index(self, actor, target_actor=None):
        if type(actor) is not int or not 0 <= actor < len(self.fighters):
            raise IllegalAction('Actor is outside the roster')
        if target_actor is None:
            candidates = self._enemies(actor) or self._enemies(actor, conscious=False)
            target_actor = min(candidates, key=lambda i: (self.fighters[i].health, i))
        target_actor = super()._target_index(actor, target_actor)
        if self.teams[target_actor] == self.teams[actor]:
            raise IllegalAction('An offensive target must belong to another team')
        return target_actor

    def observe(self, actor, target_actor=None):
        target_actor = self._target_index(actor, target_actor)
        basic = super().observe(actor, target_actor)
        return GroupObservation(**vars(basic), actor=actor, focus_target=target_actor,
                                fighters=tuple(self._view(f) for f in self.fighters), teams=self.teams)

    def _target_choices(self, actor, choices):
        enemies = self._enemies(actor)
        result = []
        for action in choices:
            if is_fast(action.kind):
                result.extend(replace(action, targets=pair) for pair in product(enemies, repeat=2))
            elif action.kind in ATTACK_KINDS:
                result.extend(TargetAction(action.kind, target_actor=target) for target in enemies)
            elif action.kind != 'move':
                result.append(action)
        return tuple(result)

    def legal_actions(self, actor):
        return self._target_choices(actor, super().legal_actions(actor))

    def _blade_bonus_actions(self, actor):
        return self._target_choices(actor, super()._blade_bonus_actions(actor))

    def _fast_targets(self, actor, action):
        if action.targets is None:
            raise IllegalAction('Group Fast Strikes must declare one target for each arm')
        return super()._fast_targets(actor, action)

    def _attack_targets_available(self, actor):
        return bool(self._enemies(actor))

    def _reaction_source_available(self, event):
        return self.fighters[event.source].conscious

    def _move(self, actor, move, *, as_standard=False):
        if not isinstance(move, Move) or move != Move() or as_standard:
            raise IllegalAction('Group positioning is not implemented; only stay is available')
        return super()._move(actor, move, as_standard=as_standard)

    def _validate_knockback(self, actor, spaces):
        if spaces > 0:
            raise NotImplementedError('Group knockback needs individual positions; damage was not applied')

    def _sync_stun(self, subject):
        instances = [effect for effect in self._timed_stuns if effect.subject == subject]
        fighter = self.fighters[subject]
        fighter.stunned_by = instances[0].source if instances else None
        fighter.stun_expires_on_actor_turn = instances[0].deadlines[0].occurrence if instances else None

    def _apply_stun(self, actor, target_actor):
        token = f'stunned:{actor}:{target_actor}'
        deadline = self.turn_counts[actor] + 1
        effect = TimedEffect(token, 'stunned', target_actor, actor,
                             (TimePoint(Boundary.TURN_START, deadline, actor),), ('HR-02', 'COND-02'))
        self._timed_stuns = tuple(item for item in self._timed_stuns if item.token != token) + (effect,)
        self._sync_stun(target_actor)
        self.fighters[target_actor].stance = False
        self._record('condition_start', effect.rules, actor=self.fighters[target_actor].profile.name,
                     condition='stunned', expires_on_actor=self.fighters[actor].profile.name,
                     source_turn_count=deadline, instance=token)

    def _start_turn_effects(self, actor):
        now = TimePoint(Boundary.TURN_START, self.turn_counts[actor], actor)
        plan = expiration_plan(self._timed_stuns, now)
        self._timed_stuns = plan.remaining
        for effect in plan.expired:
            self._record('condition_instance_end', effect.rules,
                         actor=self.fighters[effect.subject].profile.name, condition='stunned',
                         instance=effect.token, expires_on_actor=self.fighters[effect.source].profile.name)
        for subject in sorted({effect.subject for effect in plan.expired}):
            self._sync_stun(subject)
            if self.fighters[subject].stunned_by is None:
                self._record('condition_end', ('COND-02',),
                             actor=self.fighters[subject].profile.name, condition='stunned')
        fighter = self.fighters[actor]
        if fighter.dodging:
            fighter.dodging = False
            self._record('dodge_end', ('ACT-07',), actor=fighter.profile.name)

    def _heal(self, actor, amount, rule):
        fighter = self.fighters[actor]
        if fighter.health > -fighter.profile.max_health:
            super()._heal(actor, amount, rule)

    def _end_turn_effects(self, actor):
        fighter = self.fighters[actor]
        if fighter.health > -fighter.profile.max_health:
            super()._end_turn_effects(actor)

    def _inactive_turn(self, actor):
        if self.active_actor is not None:
            raise RuntimeError('Nested turn')
        fighter = self.fighters[actor]
        self.active_actor = actor
        fighter.standard_available = fighter.movement_available = False
        try:
            self.turn_counts[actor] += 1
            self._start_turn_effects(actor)
            self.turns += 1
            self._record('turn_start', ('ACT-01', 'COND-03'), actor=fighter.profile.name,
                         reactions=fighter.reactions)
            self._record('turn_skipped', ('COND-03',), actor=fighter.profile.name,
                         reason='dead' if fighter.health <= -fighter.profile.max_health else 'unconscious')
            self._end_turn_effects(actor)
            self._record('turn_end', ('ACT-01',), actor=fighter.profile.name,
                         health=fighter.health, focus=fighter.focus)
            self.damage_timeline[self.round] = tuple(f.damage_dealt for f in self.fighters)
        finally:
            self.active_actor = None

    def _outcome(self):
        living = {team for team, fighter in zip(self.teams, self.fighters) if fighter.conscious}
        if len(living) == 0:
            return 'draw', None
        if len(living) == 1:
            return 'win', next(iter(living))
        return None

    def _finish(self, outcome, winner, bonus_occurred):
        fields = ('damage_dealt', 'damage_taken', 'damage_mitigated', 'healing_effective',
                  'focus_spent', 'attacks', 'hits', 'fantastic_hits', 'ripostes',
                  'stuns_applied', 'blade_bonus_actions')
        metrics = tuple({**{key: getattr(fighter, key) for key in fields},
                         **{f'damage_round{horizon}': (fighter.damage_dealt if self.round <= horizon else
                            self.damage_timeline[horizon][index]) for horizon in (3, 5, 10)}}
                        for index, fighter in enumerate(self.fighters))
        return GroupResult(self.seed, winner, outcome, self.round, self.turns, bonus_occurred,
                           self.teams, tuple(f.health for f in self.fighters),
                           tuple(f.focus for f in self.fighters), metrics, tuple(self.log),
                           self.initiative_roles, self.initiative_tie_order,
                           self.resolved_initiative_order)
