"""Experimental Point-Blank Parry with ordinary and Fast Hands reactions."""

from dataclasses import dataclass

from blacklight.engine import IllegalAction, ReactionEvent
from .point_blank_parry import ParryTrigger, point_blank_parry
from .ranged_powers_duel import RangedPowersPolicy
from .reaction_pools import ReactionPools
from .smg_duel import SubmachineDuel


@dataclass(frozen=True)
class ParryPolicy(RangedPowersPolicy):
    prefer_parry: bool = True
    prefer_fast_hands: bool = True

    def __post_init__(self):
        super().__post_init__()
        if type(self.prefer_parry) is not bool or type(self.prefer_fast_hands) is not bool:
            raise ValueError('Reaction preferences must be boolean')

    def choose_miss_reaction(self, observation, options):
        if self.prefer_parry and 'point_blank_parry' in options:
            return 'point_blank_parry'
        if 'riposte' in options and self.use_riposte(observation):
            return 'riposte'
        return None

    def choose_parry_pool(self, observation, options):
        preferred = 'fast_hands' if self.prefer_fast_hands else 'ordinary'
        return preferred if preferred in options else options[0]


class ParryDuel(SubmachineDuel):
    """Two combatants; reaction powers use separate pools and a common trigger ledger.

    The inherited host still blocks self-incapacitating Ram. This class is not
    registered with the certified generic runner.
    """

    execution_scope = 'experimental_parry_smg_double_tap_duel'
    additional_experimental_powers = frozenset({'double_tap', 'slow_motion_dodge',
                                                 'point_blank_parry', 'fast_hands'})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fast_hands_remaining = [0, 0]
        self.missed_attack_modes = {}
        for fighter, policy in zip(self.fighters, self.policies):
            p = fighter.profile
            if ('point_blank_parry' in p.powers and (p.rank < 2 or p.ranged_range < 1)
                    or 'fast_hands' in p.powers and (p.rank < 3 or 'point_blank_parry' not in p.powers)):
                raise ValueError('Invalid Point-Blank Parry or Fast Hands prerequisites')
            if (not callable(getattr(policy, 'choose_miss_reaction', None))
                    or not callable(getattr(policy, 'choose_parry_pool', None))):
                raise ValueError('Both policies must explicitly choose missed-attack reactions')

    def _reset_reactions_for_round(self):
        super()._reset_reactions_for_round()
        for actor, fighter in enumerate(self.fighters):
            self.fast_hands_remaining[actor] = int('fast_hands' in fighter.profile.powers)
            if self.fast_hands_remaining[actor]:
                self._record('fast_hands_reset', ('CORE-P99-FAST-HANDS',), actor=fighter.profile.name,
                             reactions=1)

    def _queue_reaction(self, event):
        attack = next((row for row in reversed(self.log)
                       if row.get('type') in ('attack', 'ram_attack')
                       and row.get('trigger') == event.trigger), None)
        if attack is None or attack.get('mode') is None:
            raise RuntimeError('Missed attack has no traceable reaction source')
        self.missed_attack_modes[event.trigger] = attack['mode']
        return super()._queue_reaction(event)

    def _attack(self, actor, kind, *, reaction=False, offhand=None, fast_strike=None,
                prepared_check=None, target_actor=None):
        target = self._target_index(actor, target_actor)
        result = super()._attack(actor, kind, reaction=reaction, offhand=offhand,
                                 fast_strike=fast_strike, prepared_check=prepared_check,
                                 target_actor=target)
        if (kind == 'ranged' and not result.success
                and 'point_blank_parry' in self.fighters[target].profile.powers):
            attack = next(event for event in reversed(self.log) if event.get('type') == 'attack')
            trigger = attack['trigger']
            self._queue_reaction(ReactionEvent('riposte', target, actor, trigger))
            self._record('reaction_queued', ('ACT-03', 'CORE-P112-PARRY'),
                         actor=self.fighters[target].profile.name, trigger=trigger,
                         source=self.fighters[actor].profile.name)
        return result

    def _drain_events(self):
        processed = 0
        while self.pending:
            processed += 1
            if processed > 16:
                raise RuntimeError('Reaction queue exceeded safety bound')
            event = self.pending.popleft()
            self._reaction_dequeued(event)
            if event.kind != 'riposte':
                raise RuntimeError('Unrecognized pending event')
            defender, source = self.fighters[event.reactor], self.fighters[event.source]
            p = defender.profile
            if 'point_blank_parry' in p.powers:
                self._record('reaction_considered', ('ACT-03', 'CORE-P112-PARRY'), actor=p.name,
                             trigger=event.trigger, source=source.profile.name)
            distance = self._distance_between(event.reactor, event.source)
            if (not defender.conscious or defender.stunned_by is not None
                    or event.trigger in defender.reacted_to or not self._reaction_source_available(event)):
                continue
            choices = []
            source_mode = self.missed_attack_modes.get(event.trigger)
            if source_mode is None:
                raise RuntimeError('Missed attack reaction has no source mode')
            if ('riposte' in p.powers and source_mode != 'ranged'
                    and defender.reactions > 0 and distance <= 1):
                choices.append('riposte')
            if ('point_blank_parry' in p.powers and source.conscious and distance <= 2 and defender.focus >= 6
                    and (defender.reactions > 0 or self.fast_hands_remaining[event.reactor] > 0)):
                choices.append('point_blank_parry')
            if not choices:
                continue
            observation = self.observe(event.reactor, event.source)
            chosen = self.policies[event.reactor].choose_miss_reaction(observation, tuple(choices))
            if chosen is None:
                continue
            if chosen not in choices:
                raise IllegalAction('Policy selected an unavailable missed-attack reaction')
            if chosen == 'riposte':
                defender.reactions -= 1
                defender.reacted_to.add(event.trigger)
                defender.ripostes += 1
                self._record('reaction_spent', ('ACT-03', 'ACT-04', 'POW-06'),
                             actor=p.name, trigger=event.trigger, remaining=defender.reactions)
                attack = self.policies[event.reactor].choose_riposte_attack(observation)
                if (attack.focus != 0 or attack.offhand is not None
                        or attack.kind not in ('melee', 'blade', 'claw', 'hammer')
                        or attack.kind != 'melee' and attack.kind not in p.weapons):
                    raise IllegalAction('Riposte policy selected an invalid close attack')
                self._attack(event.reactor, attack.kind, reaction=True, target_actor=event.source)
                continue
            pools = tuple(name for name, count in (('ordinary', defender.reactions),
                          ('fast_hands', self.fast_hands_remaining[event.reactor])) if count > 0)
            pool = self.policies[event.reactor].choose_parry_pool(observation, pools)
            if pool not in pools:
                raise IllegalAction('Policy selected an unavailable reaction pool')
            state = ReactionPools(defender.reactions, self.fast_hands_remaining[event.reactor],
                                  frozenset(defender.reacted_to))
            trigger = ParryTrigger(True, p.rank, True, True, True, distance, defender.focus,
                                   p.ranged_range > 0, True, event.trigger)
            transaction = point_blank_parry(trigger, state, pool=pool)
            defender.reactions = transaction.reactions_after.ordinary
            self.fast_hands_remaining[event.reactor] = transaction.reactions_after.fast_hands
            defender.reacted_to.add(event.trigger)
            self._record('reaction_spent', ('ACT-03', 'ACT-04', 'CORE-P112-PARRY'), actor=p.name,
                         trigger=event.trigger, remaining=defender.reactions, source='point_blank_parry',
                         pool=pool, fast_hands_remaining=self.fast_hands_remaining[event.reactor])
            before_focus = defender.focus
            defender.focus = transaction.focus_after
            defender.focus_spent += 5
            self._record('focus_spent', ('RES-01', 'CORE-P112-PARRY'), actor=p.name, amount=5,
                         focus_before=before_focus, focus_after=defender.focus,
                         reaction=True, source='point_blank_parry', trigger=event.trigger)
            self._record('parry_start', ('CORE-P112-PARRY',), actor=p.name, target=source.profile.name,
                         source_trigger=event.trigger, pool=pool)
            result = self._attack(event.reactor, 'ranged', target_actor=event.source)
            attack = next(entry for entry in reversed(self.log) if entry.get('type') == 'attack')
            attack['reaction'] = True
            attack['reaction_power'] = 'point_blank_parry'
            attack['source_trigger'] = event.trigger
            bleeding = result.success and result.fantastic and not attack['ammunition_immunity']
            if bleeding:
                source.bleeding = max(source.bleeding, 5)
                self._record('condition_start', ('COND-01', 'CORE-P112-PARRY'),
                             actor=source.profile.name, condition='bleeding', intensity=5,
                             trigger=attack['trigger'])
            self._record('parry_end', ('CORE-P112-PARRY',), actor=p.name, target=source.profile.name,
                         source_trigger=event.trigger, trigger=attack['trigger'], bleeding=bleeding)
