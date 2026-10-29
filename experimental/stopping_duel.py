"""Experimental Stopping Power with a separately checked optional follow-up."""

from dataclasses import dataclass

from blacklight.engine import Action, IllegalAction
from .parry_duel import ParryDuel, ParryPolicy


@dataclass(frozen=True)
class StoppingPolicy(ParryPolicy):
    prefer_stopping: bool = False
    use_stopping_followup: bool = True

    def __post_init__(self):
        super().__post_init__()
        if type(self.prefer_stopping) is not bool or type(self.use_stopping_followup) is not bool:
            raise ValueError('Stopping Power preferences must be boolean')

    def choose_action(self, observation):
        action = super().choose_action(observation)
        if (self.prefer_stopping and action.kind in ('ranged', 'double_tap')
                and 'stopping_power' in observation.me.powers and observation.me.focus >= 6):
            return Action('stopping_power')
        return action

    def choose_stopping_followup(self, observation):
        return self.use_stopping_followup


class StoppingDuel(ParryDuel):
    """Core p.121 / PDF p.122, in the existing experimental duel scope."""

    execution_scope = 'experimental_stopping_power_parry_duel'
    additional_experimental_powers = ParryDuel.additional_experimental_powers | {'stopping_power'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stopping_use_seq = 0
        for fighter, policy in zip(self.fighters, self.policies):
            p = fighter.profile
            if ('stopping_power' in p.powers and
                    (p.rank < 2 or 'double_tap' not in p.powers or p.ranged_range < 1)):
                raise ValueError('Stopping Power requires Rank 2, Double Tap and a ranged attack')
            if not callable(getattr(policy, 'choose_stopping_followup', None)):
                raise ValueError('Both policies must decide whether to take the follow-up')

    def legal_actions(self, actor):
        actions = super().legal_actions(actor)
        fighter = self.fighters[actor]
        if (Action('ranged') in actions and 'stopping_power' in fighter.profile.powers
                and fighter.focus >= 6):
            actions += (Action('stopping_power'),)
        return actions

    def _stopping_attack(self, actor, target, use_id, role):
        result = self._attack(actor, 'ranged', target_actor=target)
        attack = next((event for event in reversed(self.log) if event.get('type') == 'attack'), None)
        if (attack is None or attack.get('actor') != self.fighters[actor].profile.name
                or attack.get('target') != self.fighters[target].profile.name or attack.get('mode') != 'ranged'):
            raise RuntimeError('Stopping Power could not associate its ranged attack')
        attack['stopping_use_id'] = use_id
        attack['stopping_role'] = role
        self._drain_events()
        return result, attack['trigger']

    def _act(self, actor, action):
        if not isinstance(action, Action) or action.kind != 'stopping_power':
            return super()._act(actor, action)
        if action != Action('stopping_power') or action not in self.legal_actions(actor):
            raise IllegalAction('Stopping Power requires a standard action and 5 Focus')
        fighter = self.fighters[actor]
        target_index = self._target_index(actor)
        target = self.fighters[target_index]
        fighter.standard_available = False
        self.stopping_use_seq += 1
        use_id = self.stopping_use_seq
        self._record('stopping_start', ('CORE-P121-STOPPING',), actor=fighter.profile.name,
                     target=target.profile.name, use_id=use_id, distance=self.distance)
        before = fighter.focus
        fighter.focus -= 5
        fighter.focus_spent += 5
        self._record('focus_spent', ('RES-01', 'CORE-P121-STOPPING'), actor=fighter.profile.name,
                     amount=5, focus_before=before, focus_after=fighter.focus,
                     source='stopping_power', stopping_use_id=use_id)
        first, trigger = self._stopping_attack(actor, target_index, use_id, 'initial')
        eligible = (first.success and first.fantastic and fighter.conscious
                    and fighter.stunned_by is None and target.conscious)
        used = False
        if eligible:
            used = self.policies[actor].choose_stopping_followup(self.observe(actor, target_index))
            if type(used) is not bool:
                raise IllegalAction('Stopping follow-up decision must be boolean')
        self._record('stopping_decision', ('CORE-P121-STOPPING',), actor=fighter.profile.name,
                     target=target.profile.name, use_id=use_id, trigger=trigger,
                     eligible=eligible, used=used)
        if used:
            self._stopping_attack(actor, target_index, use_id, 'followup')
        self._record('stopping_end', ('CORE-P121-STOPPING',), actor=fighter.profile.name,
                     target=target.profile.name, use_id=use_id, followed_up=used)
