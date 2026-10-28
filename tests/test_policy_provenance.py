"""Custom policies must not silently acquire built-in provenance claims."""

from dataclasses import dataclass
from pathlib import Path
import unittest

from blacklight.policies import ATTACK, RulePolicy
from combatants.runner import run_batch, run_duel
from combatants.sheets import load_sheet


ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / 'characters/victor_halle/rank3_2026-10-27_split_fast.json'
FOE = ROOT / 'characters/examples/synthetic_rank4_split_fast.json'


@dataclass(frozen=True)
class CustomPolicy(RulePolicy):
    def choose_action(self, observation):
        return super().choose_action(observation)


class TestPolicyProvenance(unittest.TestCase):
    def test_known_policy_is_marked_as_project_builtin(self):
        result = run_duel(load_sheet(HERO), load_sheet(FOE), ATTACK, ATTACK,
                          seed=41, max_rounds=2)
        self.assertEqual(result['policy_provenance'], 'project_builtin')

    def test_custom_subclass_is_explicitly_unverified_in_duel_and_batch(self):
        hero, foe = load_sheet(HERO), load_sheet(FOE)
        custom = CustomPolicy('external-test', weapon='hammer')
        duel = run_duel(hero, foe, custom, ATTACK, seed=41, max_rounds=2)
        batch = run_batch(hero, foe, custom, ATTACK, n=2, master_seed=41,
                          max_rounds=2, audit_every=1)
        for result in (duel, batch):
            self.assertEqual(result['policy_provenance'], 'external_unverified')
            self.assertIn('tests/test_policy_provenance.py', result['source_sha256'])
            self.assertIn('transitive', result['runtime']['external_policy_dependency_scope'])


if __name__ == '__main__':
    unittest.main()
