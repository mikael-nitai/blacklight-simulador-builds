import unittest
from hashlib import sha256

from blacklight.batch_audit import audit_batch_metadata
from combatants.runner import run_batch
from combatants.sheets import sheet_record
from scripts.current_study_dev import INPUTS, configurations
from scripts.current_study_confirm import POLICIES, confirmation_cell_hash
from scripts.current_study_holdout import SCENARIOS, holdout_configurations


class HoldoutConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.inputs = tuple(path.read_bytes() for path in INPUTS)
        self.hero, self.policies, self.scenarios = holdout_configurations(self.inputs)

    def test_holdout_keeps_original_candidate_policies(self):
        _, original, _ = configurations(self.inputs)
        self.assertEqual(self.policies, original)
        self.assertEqual(tuple(self.scenarios), SCENARIOS)

    def test_changes_are_explicit(self):
        mirror, mirror_policy, distance, board = self.scenarios['mirror_blade']
        self.assertEqual(distance, 4)
        self.assertIsNone(board)
        self.assertEqual((mirror_policy.weapon, mirror_policy.offhand, mirror_policy.effect_limb),
                         ('blade', 'hammer', 0))
        self.assertTrue(mirror_policy.prefer_fast and mirror_policy.shield_end_turn)
        sturdy = [x for x in sheet_record(self.scenarios['rank4_sturdy2'][0])['features']
                  if x['id'] == 'sturdy']
        self.assertEqual(sturdy[0]['level'], 2)
        _, gunner, distance, board = self.scenarios['gunner_open']
        self.assertEqual((distance, board), (8, None))
        self.assertTrue(gunner.kite and gunner.move_after_attack and gunner.treat_bleeding)

    def test_scenarios_run_and_pass_batch_audit(self):
        for name, (opponent, opponent_policy, distance, board) in self.scenarios.items():
            for policy_name in POLICIES:
                with self.subTest(scenario=name, policy=policy_name):
                    policy = self.policies[policy_name]
                    result = run_batch(self.hero, opponent, policy, opponent_policy, n=2,
                                       master_seed=91, initial_distance=distance, max_rounds=30,
                                       audit_every=1, battlefield=board, extended_metrics=True)
                    self.assertEqual(audit_batch_metadata(result), [])
                    self.assertEqual(sum(result['outcomes'].values()), 2)
                    cell = confirmation_cell_hash(self.hero, opponent, policy, opponent_policy,
                                                  distance, board)
                    expected = [int.from_bytes(sha256(f'character-batch-v2|91|{cell}|{i}'.encode()).digest()[:8],
                                               'big') for i in range(2)]
                    self.assertEqual([x['seed'] for x in result['audited_traces']], expected)
