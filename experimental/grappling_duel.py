"""Experimental two-combatant Grappling Technique integration.

This host is intentionally restricted and is not a certified runner. It
rejects attacks while a hold persists and does not model carrying or grappling
with biological weapons; target Escape and voluntary release remain possible.
"""

from dataclasses import asdict, dataclass

from blacklight.dice import resolve_check
from blacklight.engine import Action, IllegalAction, Move
from .adaptive_armed_melee import DeclaredArmedMeleeDuel, ShieldAwarePolicy
from .grappling import GrapplingState, escape, grappling_technique
from .prone_duel import ProneObservation
from .reaction_pools import ReactionPools


@dataclass(frozen=True)
class GrapplingObservation(ProneObservation):
    me_grabbed: bool = False
    me_pinned: bool = False
    me_grabbing: bool = False


@dataclass(frozen=True)
class GrapplingPolicy(ShieldAwarePolicy):
    prefer_grapple: bool = False
    escape_reaction: bool = True
    release_hold: bool = False

    def __post_init__(self):
        super().__post_init__()
        if any(type(v) is not bool for v in (self.prefer_grapple, self.escape_reaction, self.release_hold)):
            raise ValueError('Grappling choices must be boolean')

    def choose_move(self, observation):
        if observation.me_grabbed or observation.me_grabbing:
            return None
        return super().choose_move(observation)

    def choose_post_move(self, observation):
        if observation.me_grabbed or observation.me_grabbing:
            return Move()
        return super().choose_post_move(observation)

    def choose_action(self, observation):
        if observation.me_grabbed:
            return Action('escape')
        if observation.me_grabbing:
            return Action('release_hold') if self.release_hold else Action('wait')
        if (self.prefer_grapple and 'grappling_technique' in observation.me.powers
                and observation.me.focus >= 6 and observation.distance <= 1):
            return Action('grappling_technique')
        return super().choose_action(observation)

    def choose_miss_reaction(self, observation, options):
        if observation.me_grabbed or observation.me_grabbing:
            return None
        return super().choose_miss_reaction(observation, options)

    def choose_escape_reaction(self, observation):
        return self.escape_reaction


class GrapplingDuel(DeclaredArmedMeleeDuel):
    execution_scope = 'experimental_grappling_two_combatant_duel'
    additional_experimental_powers = DeclaredArmedMeleeDuel.additional_experimental_powers | {'grappling_technique'}

    def __init__(self, *args, escape_trigger_mode, **kwargs):
        if escape_trigger_mode not in ('attack', 'condition'):
            raise ValueError('Choose the explicit Escape trigger identity hypothesis')
        self.escape_trigger_mode = escape_trigger_mode
        self.holder = None
        self.pinned_target = False
        super().__init__(*args, **kwargs)
        if any(not isinstance(policy, GrapplingPolicy) for policy in self.policies):
            raise ValueError('Both policies must support explicit grappling choices')
        if any('grappling_technique' in f.profile.powers and
               (f.profile.rank < 2 or 'mighty' in f.profile.powers) for f in self.fighters):
            raise ValueError('Grappling requires Rank 2; Mighty/knockback choice is not integrated')

    def observe(self, actor, target_actor=None):
        base = super().observe(actor, target_actor)
        held = self.holder is not None and actor != self.holder
        return GrapplingObservation(base.me, base.foe, base.distance, base.round, base.bonus_round,
                                    base.terrain, base.me_prone, base.foe_prone,
                                    held, held and self.pinned_target, actor == self.holder)

    def _move(self, actor, move, *, as_standard=False):
        if self.holder is not None:
            if not isinstance(move, Move) or move.direction != 'stay' or move.steps != 0 or as_standard:
                raise IllegalAction('Moving while entangled is unsupported')
            return
        return super()._move(actor, move, as_standard=as_standard)

    def legal_actions(self, actor):
        actions = super().legal_actions(actor)
        if not actions:
            return actions
        if self.holder is not None:
            return (Action('wait'), Action('release_hold')) if actor == self.holder else (Action('wait'), Action('escape'))
        fighter = self.fighters[actor]
        if ('grappling_technique' in fighter.profile.powers and fighter.focus >= 6 and self.distance == 1):
            actions += (Action('grappling_technique'),)
        return actions

    def _state(self, holder, target, *, attacker_focus=None, attacker_standard=None, target_health=None):
        a, b = self.fighters[holder], self.fighters[target]
        return GrapplingState(attacker_rank=a.profile.rank,
            attacker_focus=a.focus if attacker_focus is None else attacker_focus,
            attacker_standard=a.standard_available if attacker_standard is None else attacker_standard,
            attacker_conscious=a.conscious, attacker_stunned=a.stunned_by is not None,
            target_health=b.health if target_health is None else target_health,
            target_standard=b.standard_available, target_stunned=b.stunned_by is not None,
            target_reactions=ReactionPools(b.reactions, self.fast_hands_remaining[target], frozenset(b.reacted_to)),
            distance=self.distance, grabbed=self.holder is not None, pinned=self.pinned_target)

    def _escape(self, target, *, timing, trigger=None):
        holder = self.holder
        if holder is None or holder == target:
            raise IllegalAction('No opponent is holding this actor')
        fighter, other = self.fighters[target], self.fighters[holder]
        if (timing not in ('standard', 'reaction') or not fighter.conscious or fighter.stunned_by is not None
                or timing == 'standard' and (not fighter.standard_available or trigger is not None)
                or timing == 'reaction' and (type(trigger) is not int or trigger < 1
                    or fighter.reactions < 1 or trigger in fighter.reacted_to)):
            raise IllegalAction('Escape is unavailable')
        before = self._state(holder, target)
        mighty = fighter.profile.melee_bonus if 'mighty' in fighter.profile.powers else 0
        result, traces = resolve_check(self.rng, fighter.profile.melee + mighty,
            other.profile.melee_defense, troubles=int(self.pinned_target),
            chooser=lambda roll, mod, tn: self.policies[target].choose_edge_die(roll, mod, tn, 'escape'))
        transaction = escape(before, timing=timing, melee=fighter.profile.melee, mighty=mighty,
            grabber_melee_defense=other.profile.melee_defense, roll=result.roll, rerolls=traces,
            trigger=trigger)
        fighter.standard_available = transaction.after.target_standard
        if timing == 'reaction':
            fighter.reactions = transaction.after.target_reactions.ordinary
            fighter.reacted_to = set(transaction.after.target_reactions.spent_triggers)
            self._record('reaction_spent', ('ACT-03', 'CORE-P31-ESCAPE'), actor=fighter.profile.name,
                         source='grapple_escape', trigger=trigger, remaining=fighter.reactions)
        if transaction.success:
            self.holder = None
            self.pinned_target = False
        self._record('grapple_escape', ('CORE-P30-ESCAPE',), actor=fighter.profile.name,
                     target=other.profile.name, timing=timing, trigger=trigger,
                     transaction=asdict(transaction))

    def _act(self, actor, action):
        if not isinstance(action, Action):
            raise IllegalAction('Invalid action request')
        if action.kind not in ('grappling_technique', 'escape', 'release_hold'):
            if self.holder is not None and action != Action('wait'):
                raise IllegalAction('This experimental hold permits only Escape, release or wait')
            return super()._act(actor, action)
        if action not in self.legal_actions(actor):
            raise IllegalAction('Grappling action is unavailable')
        if action.kind == 'escape':
            self._escape(actor, timing='standard')
            return
        if action.kind == 'release_hold':
            self.holder, self.pinned_target = None, False
            self._record('grapple_release', ('CORE-P30-GRAB',), actor=self.fighters[actor].profile.name)
            self._act(actor, Action('wait'))
            return
        attacker = self.fighters[actor]
        target = self._target_index(actor)
        defender = self.fighters[target]
        initial_focus, initial_health = attacker.focus, defender.health
        attacker.standard_available = False
        attacker.focus -= 5
        attacker.focus_spent += 5
        self._record('grapple_start', ('CORE-P101-GRAPPLE',), actor=attacker.profile.name,
                     target=defender.profile.name)
        self._record('focus_spent', ('RES-01', 'CORE-P101-GRAPPLE'), actor=attacker.profile.name,
                     amount=5, focus_before=initial_focus, focus_after=attacker.focus,
                     source='grappling_technique')
        check = self._attack(actor, 'melee', target_actor=target)
        attack = next(e for e in reversed(self.log) if e.get('type') == 'attack')
        transaction = grappling_technique(self._state(actor, target, attacker_focus=initial_focus,
            attacker_standard=True, target_health=initial_health), has_power=True,
            attack_success=check.success, fantastic_success=check.success and check.fantastic,
            applied_damage=attack['damage'], trigger=attack['trigger'])
        if transaction.after.attacker_focus != attacker.focus or transaction.after.target_health != defender.health:
            raise RuntimeError('Grapple transaction diverged from attack')
        if check.success:
            self.holder, self.pinned_target = actor, check.fantastic
        self._record('grapple_end', ('CORE-P101-GRAPPLE',), actor=attacker.profile.name,
                     target=defender.profile.name, trigger=attack['trigger'], transaction=asdict(transaction))
        if check.success and defender.conscious and defender.stunned_by is None and defender.reactions:
            trigger = attack['trigger']
            if self.escape_trigger_mode == 'condition':
                self.trigger_seq += 1
                trigger = self.trigger_seq
            if (trigger not in defender.reacted_to and
                    self.policies[target].choose_escape_reaction(self.observe(target, actor))):
                self._escape(target, timing='reaction', trigger=trigger)
        self._drain_events()
