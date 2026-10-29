from dataclasses import replace
import unittest

from experimental.ram_trigger import Approach
from experimental.ram_transaction import RamState, execute_ram


class RamTransactionTests(unittest.TestCase):
    def setUp(self):
        self.first = Approach('Victor', 'oponente', 2, 'movement', 10, 5, 5)
        self.second = Approach('Victor', 'oponente', 2, 'standard', 5, 1, 5)
        self.state = RamState(150, 100, 2, True, False)
        self.args = dict(success=True, fantastic_success=False, full_dice=6, ability=6,
                         target_reduction=2, attacker_reduction=1,
                         target_faces=(1, 2, 3, 4, 5, 6), self_pool='shared')

    def test_success_is_atomic_and_spends_one_reaction(self):
        result = execute_ram(self.state, self.first, self.second, **self.args)
        self.assertEqual(result.before, self.state)
        self.assertEqual(result.after, RamState(124, 58, 1, True, False))
        self.assertEqual(self.state, RamState(150, 100, 2, True, False))

    def test_miss_still_spends_reaction_without_damage(self):
        args = {**self.args, 'success': False, 'target_faces': ()}
        result = execute_ram(self.state, self.first, self.second, **args)
        self.assertEqual(result.after, RamState(150, 100, 1, True, False))

    def test_fantastic_applies_prone_and_can_incapacitate_attacker(self):
        state = replace(self.state, attacker_health=20)
        result = execute_ram(state, self.first, self.second,
                             **{**self.args, 'fantastic_success': True})
        self.assertEqual(result.after, RamState(-6, 37, 1, False, True))

    def test_rejects_unavailable_reaction_incapacity_or_bad_approach(self):
        for state in (replace(self.state, reactions=0), replace(self.state, attacker_able=False),
                      replace(self.state, attacker_health=0), replace(self.state, target_health=0)):
            with self.subTest(state=state), self.assertRaises(ValueError):
                execute_ram(state, self.first, self.second, **self.args)
        with self.assertRaises(ValueError):
            execute_ram(self.state, self.first, replace(self.second, after=2), **self.args)

    def test_rejects_forged_impact_without_mutating_state(self):
        with self.assertRaises(ValueError):
            execute_ram(self.state, self.first, self.second, **{**self.args, 'target_faces': (7,)})
        self.assertEqual(self.state, RamState(150, 100, 2, True, False))

    def test_existing_prone_state_is_preserved_on_miss(self):
        state = replace(self.state, target_prone=True)
        args = {**self.args, 'success': False, 'target_faces': ()}
        self.assertTrue(execute_ram(state, self.first, self.second, **args).after.target_prone)
