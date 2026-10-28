"""Static gates for preregistered current-rule physical study configuration."""

import unittest

from combatants.duel_adapter import CURRENT_RULESET, compile_duel
from scripts.current_study_dev import (INPUTS, MASTER_SEED, N_PER_CELL, POLICIES,
                                       SCENARIOS, configurations, output_path)


class TestCurrentStudyConfiguration(unittest.TestCase):
    def test_fixed_candidates_and_synthetic_scenarios_are_legal_for_adapter(self):
        hero, candidates, scenarios = configurations(tuple(path.read_bytes() for path in INPUTS))
        self.assertEqual(set(candidates), set(POLICIES))
        self.assertEqual(tuple(scenarios), SCENARIOS)
        self.assertEqual((N_PER_CELL, MASTER_SEED), (1000, 827104291))
        self.assertEqual((hero.rank, hero.resources['health'], hero.resources['focus']), (3, 150, 90))
        self.assertEqual(hero.ruleset, CURRENT_RULESET)
        for policy in candidates.values():
            self.assertTrue(policy.shield_react)
            self.assertTrue(policy.riposte)
            self.assertFalse(policy.knockback_stance)
            self.assertFalse(policy.open_stance)
            self.assertFalse(policy.shield_end_turn)
            self.assertIsNone(policy.heal_missing)
        for opponent, policy, distance, board in scenarios.values():
            self.assertNotEqual(hero.name, opponent.name)
            self.assertEqual(opponent.ruleset, CURRENT_RULESET)
            self.assertFalse(policy.knockback_stance)
            self.assertTrue(compile_duel(opponent))
            self.assertTrue((board is None) != (distance is None))
        self.assertEqual(scenarios['mirror'][0].id, 'synthetic_victor_mirror')
        self.assertTrue(any(row.get('kind') == 'synthetic'
                            for row in scenarios['mirror'][0].provenance))
        self.assertNotEqual(output_path('mirror', 'bare'), output_path('rank4', 'bare'))
