from copy import deepcopy
import unittest
from unittest.mock import patch

from blacklight.dice import DieRoll, Result
from experimental.ram_rolled import audit_rolled_table_ram, rolled_table_ram
from experimental.ram_transaction import RamState
from experimental.ram_trigger import Approach


class RolledRamTests(unittest.TestCase):
    def setUp(self):
        self.state = RamState(150, 120, 2, True, False)
        self.first = Approach('Victor', 'Alvo', 3, 'movement', 10, 5, 5)
        self.second = Approach('Victor', 'Alvo', 3, 'standard', 5, 1, 5)
        self.args = dict(modifier=6, target_number=16, full_dice=6, ability=6,
                         target_reduction=2, attacker_reduction=1)

    def roll(self, seed, **overrides):
        return rolled_table_ram(self.state, self.first, self.second, seed=seed,
                                **{**self.args, **overrides})

    def test_seeded_rolls_are_reproducible_and_audited(self):
        self.assertEqual(self.roll(4), self.roll(4))
        results = [self.roll(seed, edges=1, troubles=0) for seed in range(200)]
        self.assertTrue(any(r['check']['success'] for r in results))
        self.assertTrue(any(not r['check']['success'] for r in results))
        self.assertTrue(any(r['parameters']['fantastic_success'] for r in results))
        self.assertTrue(any(r['parameters']['target_faces'] != r['parameters']['attacker_faces']
                            for r in results if r['check']['success']))
        for result in results:
            self.assertEqual(audit_rolled_table_ram(result), [])

    def test_ultimate_fantastic_succeeds_even_above_total(self):
        roll = Result(DieRoll(6, 1, 6), 24, True, True, True)
        with patch('experimental.ram_rolled.resolve_check', return_value=(roll, ())):
            result = self.roll(1, target_number=100)
        self.assertTrue(result['parameters']['fantastic_success'])
        self.assertTrue(result['impact']['target_prone'])
        self.assertEqual(audit_rolled_table_ram(result), [])

    def test_check_forgery_is_detected(self):
        result = self.roll(6)
        self.assertEqual(audit_rolled_table_ram(result), [])
        for key, value in (('total', 999), ('success', not result['check']['success']),
                           ('ultimate', not result['check']['ultimate']),
                           ('fantastic_roll', not result['check']['fantastic_roll'])):
            with self.subTest(key=key):
                altered = deepcopy(result)
                altered['check'][key] = value
                self.assertTrue(audit_rolled_table_ram(altered))

    def test_invalid_reaction_or_seed_is_rejected(self):
        with self.assertRaises(ValueError):
            self.roll(True)
        with self.assertRaises(ValueError):
            rolled_table_ram(RamState(150, 120, 0, True, False), self.first, self.second,
                             seed=1, **self.args)
