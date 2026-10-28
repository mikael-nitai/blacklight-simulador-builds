"""Manual initiative and adversarial trace cases for the experimental host."""

from copy import deepcopy
from dataclasses import replace
import unittest

from blacklight.engine import blacklight_profile
from combatants.group import GroupBattle, GroupPolicy
from combatants.group_initiative_audit import audit_group_initiative


class FixedDice:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        return next(self.values)


class TestGroupInitiative(unittest.TestCase):
    def setUp(self):
        base = replace(blacklight_profile(), traits=frozenset())
        self.profiles = tuple(replace(base, name=name) for name in ('NPC A', 'Jogador', 'NPC B'))
        self.policies = tuple(GroupPolicy(name, edge_mode='decline', always_wait=True)
                              for name in ('a', 'b', 'c'))
        self.roles = ('npc', 'player', 'npc')

    def battle(self, **kwargs):
        return GroupBattle(self.profiles, self.policies, teams=('a', 'b', 'a'),
                           seed=1, audit=True, **kwargs)

    def test_player_priority_and_explicit_remaining_order(self):
        battle = self.battle(initiative_roles=self.roles, initiative_tie_order=(2, 0, 1))
        battle.rng = FixedDice([2, 2, 2] * 3)
        order, fantastic = battle._initiative()
        self.assertEqual(order, (1, 2, 0))
        self.assertEqual(fantastic, (False, False, False))
        self.assertEqual(audit_group_initiative(battle.log, self.profiles, self.roles, (2, 0, 1)), [])

    def test_fantastic_precedes_role_and_roll_total_precedes_all(self):
        battle = self.battle(initiative_roles=self.roles)
        # All scores include modifier +2: 10 Fantastic, 10 common, 12 common.
        battle.rng = FixedDice([1, 1, 1, 2, 2, 4, 3, 3, 4])
        self.assertEqual(battle._initiative()[0], (2, 0, 1))
        self.assertEqual(audit_group_initiative(battle.log, self.profiles, self.roles, None), [])

    def test_higher_modifier_precedes_player_priority(self):
        self.profiles = (replace(self.profiles[0], initiative_modifier=4),
                         replace(self.profiles[1], initiative_modifier=2),
                         replace(self.profiles[2], initiative_modifier=0))
        battle = self.battle(initiative_roles=self.roles)
        # Each totals 10; the NPC's +4 outranks the player's +2.
        battle.rng = FixedDice([2, 2, 2, 2, 2, 4, 3, 3, 4])
        self.assertEqual(battle._initiative()[0], (0, 1, 2))
        self.assertEqual(audit_group_initiative(battle.log, self.profiles, self.roles, None), [])

    def test_tied_players_use_declared_order(self):
        roles = ('player', 'player', 'npc')
        battle = self.battle(initiative_roles=roles, initiative_tie_order=(1, 0, 2))
        battle.rng = FixedDice([2, 2, 2] * 3)
        self.assertEqual(battle._initiative()[0], (1, 0, 2))
        self.assertEqual(audit_group_initiative(battle.log, self.profiles, roles, (1, 0, 2)), [])

    def test_missing_role_or_unresolved_tie_is_rejected(self):
        battle = self.battle()
        with self.assertRaisesRegex(ValueError, 'roles'):
            battle._initiative()
        self.assertEqual(battle.log, [])
        battle = self.battle(initiative_roles=self.roles)
        battle.rng = FixedDice([2, 2, 2] * 3)
        with self.assertRaisesRegex(ValueError, 'tie'):
            battle._initiative()
        self.assertFalse(any(e['type'] == 'turn_start' for e in battle.log))

    def test_bad_inputs_and_falsified_trace_fail(self):
        for kwargs in ({'initiative_roles': ('player', 'npc')},
                       {'initiative_roles': ('player', 'unknown', 'npc')},
                       {'initiative_tie_order': (0, 0, 1)},
                       {'initiative_tie_order': (True, 0, 2)}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.battle(**kwargs)
        battle = self.battle(initiative_roles=self.roles, initiative_tie_order=(2, 0, 1))
        battle.rng = FixedDice([2, 2, 2] * 3)
        battle._initiative()
        for field, value in (('order', [0, 1, 2]), ('roles', ['player'] * 3),
                             ('tie_order', [0, 1, 2])):
            forged = deepcopy(battle.log)
            next(row for row in forged if row['type'] == 'group_initiative_order')[field] = value
            self.assertTrue(audit_group_initiative(forged, self.profiles, self.roles, (2, 0, 1)))

    def test_full_battle_schedule_audits_and_detects_wrong_turn(self):
        roles, tie = self.roles, (2, 0, 1)
        battle = self.battle(initiative_roles=roles, initiative_tie_order=tie, max_rounds=2)
        result = battle.run()
        self.assertEqual(audit_group_initiative(result.log, self.profiles, roles, tie), [])
        forged = deepcopy(list(result.log))
        first_turn = next(row for row in forged if row['type'] == 'turn_start')
        first_turn['actor'] = next(name for name in ('NPC A', 'Jogador', 'NPC B') if name != first_turn['actor'])
        self.assertIn('turn order differs from declared initiative',
                      audit_group_initiative(forged, self.profiles, roles, tie))


if __name__ == '__main__':
    unittest.main()
