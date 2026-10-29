"""Experimental Double Tap in a two-person Ram/Prone physical duel."""

from dataclasses import dataclass

from blacklight.engine import Action, IllegalAction
from .nonlethal_ram_duel import NonlethalRamProneDuel
from .ram_prone_duel import RamPronePolicy


@dataclass(frozen=True)
class DoubleTapPolicy(RamPronePolicy):
    prefer_double_tap: bool = True

    def __post_init__(self):
        super().__post_init__()
        if type(self.prefer_double_tap) is not bool:
            raise ValueError('Double Tap preference must be boolean')

    def choose_action(self, observation):
        action = super().choose_action(observation)
        if (self.prefer_double_tap and action.kind == 'ranged'
                and 'double_tap' in observation.me.powers and observation.distance <= 2):
            return Action('double_tap')
        return action


class DoubleTapDuel(NonlethalRamProneDuel):
    """Current table dice, existing ranged check, plus Double Tap bleeding.

    Core p.95, PDF p.96. Ammunition immunity also prevents its bleeding;
    other unmodeled forms of immunity are rejected by the surrounding host.
    """

    execution_scope = 'experimental_double_tap_ram_prone_duel'
    additional_experimental_powers = frozenset({'double_tap'})

    def legal_actions(self, actor):
        actions = super().legal_actions(actor)
        p = self.fighters[actor].profile
        if (Action('ranged') in actions and 'double_tap' in p.powers
                and self.distance <= 2):
            actions += (Action('double_tap'),)
        return actions

    def _act(self, actor, action):
        if not isinstance(action, Action) or action.kind != 'double_tap':
            return super()._act(actor, action)
        if action != Action('double_tap') or action not in self.legal_actions(actor):
            raise IllegalAction('Double Tap requires a standard action and a target within two spaces')
        fighter = self.fighters[actor]
        target_index = self._target_index(actor)
        target = self.fighters[target_index]
        fighter.standard_available = False
        self._record('double_tap_start', ('CORE-P95-DOUBLE-TAP',), actor=fighter.profile.name,
                     target=target.profile.name, distance=self.distance)
        result = self._attack(actor, 'ranged', target_actor=target_index)
        attack = next((entry for entry in reversed(self.log) if entry.get('type') == 'attack'), None)
        if attack is None or attack.get('actor') != fighter.profile.name or attack.get('mode') != 'ranged':
            raise RuntimeError('Double Tap could not associate its ranged attack')
        bleeding = result.success and result.fantastic and not attack['ammunition_immunity']
        if bleeding:
            target.bleeding = max(target.bleeding, 5)
            self._record('condition_start', ('COND-01', 'CORE-P95-DOUBLE-TAP'),
                         actor=target.profile.name, condition='bleeding', intensity=5,
                         trigger=attack['trigger'])
        self._record('double_tap_end', ('CORE-P95-DOUBLE-TAP',), actor=fighter.profile.name,
                     target=target.profile.name, trigger=attack['trigger'], bleeding=bleeding)
        self._drain_events()
