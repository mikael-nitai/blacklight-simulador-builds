"""New table boundary: DR zero and halving zero are distinct operations."""

from dataclasses import replace
from copy import deepcopy
import unittest

from blacklight.audit import audit_log
from blacklight.engine import Action, Duel, Profile
from blacklight.policies import RulePolicy
from experimental.group import GroupBattle
from experimental.group_audit import audit_group_log
from experimental.group_policies import GroupAction, GroupPolicy


class Dice:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        value = next(self.values)
        assert low <= value <= high
        return value


class TestFastZeroDiceBonus(unittest.TestCase):
    def profiles(self):
        a = Profile('A', 3, 90, 60, 6, 2, 3, 2, 16, 12, 5,
                    powers=frozenset({'fast_strikes'}))
        b = Profile('B', 3, 90, 60, 4, 2, 3, 2, 14, 12, 5, health_dr=2)
        return a, b

    def test_duel_two_components_keep_three_bonus_each_and_auditor_rejects_zero(self):
        profiles = self.profiles()
        policy = RulePolicy('control', prefer_fast=True, edge_mode='decline')
        game = Duel(profiles, (policy, policy), seed=1, audit=True, fast_zero_dice_bonus=True)
        game.round = 1
        game._reset_reactions_for_round()
        game.active_actor = 0
        game.fighters[0].standard_available = True
        game.rng, game.damage_rng = Dice([6, 6, 6]), Dice([2, 5])
        game._act(0, Action('fast_strikes'))
        attack = next(row for row in game.log if row['type'] == 'attack')
        self.assertEqual(attack['calculated_damage'], 6)
        self.assertEqual([part['ability_added'] for part in attack['damage_components']], [3, 3])
        self.assertEqual([part['faces'] for part in attack['damage_components']], [[], []])
        health = {p.name: p.max_health for p in profiles}
        focus = {p.name: p.max_focus for p in profiles}
        self.assertEqual(audit_log(game.log, health, focus), [])
        changed = deepcopy(game.log)
        row = next(row for row in changed if row['type'] == 'attack')
        row['damage_components'][0]['damage'] = 0
        self.assertTrue(any('component damage mismatch' in issue
                            for issue in audit_log(changed, health, focus)))

    def test_group_damage_and_independent_auditor_keep_bonus(self):
        a, b = self.profiles()
        profiles = (a, b, replace(b, name='C'))
        game = GroupBattle(profiles, (GroupPolicy('control'),) * 3, seed=1, audit=True,
                            fast_zero_dice_bonus=True)
        game.round = 1
        game._reset_reactions()
        game.rng, game.damage_rng = Dice([6, 6, 6]), Dice([])
        game._attack(0, GroupAction('fast_strikes', (1,)))
        row = next(row for row in game.log if row['type'] == 'attack_target')
        self.assertEqual((row['calculated_damage'], row['damage_faces']), (6, [[], []]))
        self.assertEqual(audit_group_log(game.log, profiles), [])


if __name__ == '__main__':
    unittest.main()
