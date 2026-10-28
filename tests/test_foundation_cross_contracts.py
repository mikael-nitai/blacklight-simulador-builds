"""Exercise complete-result checks across both contracts and different policies."""

from dataclasses import asdict
import unittest

from blacklight.audit import audit_profiled_log
from blacklight.engine import Duel, blacklight_profile
from blacklight.experiment import scenarios, seed_for, strategies
from blacklight.result_audit import audit_battle_result
from blacklight.rulesets import CURRENT_RULESET, LEGACY_RULESET
from blacklight.spatial_audit import audit_open_field_distance
from combatants.split_fast import SplitFastDuel, SplitFastPolicy


class TestFoundationCrossContracts(unittest.TestCase):
    def test_complete_audits_across_policies_opponents_and_versions(self):
        for engine, ruleset in ((Duel, LEGACY_RULESET), (SplitFastDuel, CURRENT_RULESET)):
            for scenario in scenarios():
                for strategy in strategies():
                    profiles = (blacklight_profile(), scenario.opponent)
                    policies = (strategy.policy, scenario.policy)
                    if engine is SplitFastDuel:
                        policies = tuple(SplitFastPolicy(**asdict(policy)) for policy in policies)
                    for index in range(5):
                        with self.subTest(ruleset=ruleset, scenario=scenario.id,
                                          strategy=strategy.id, index=index):
                            seed = seed_for('foundation-cross-contracts', scenario.id,
                                            strategy.id, index)
                            result = engine(profiles, policies, seed=seed,
                                            initial_distance=scenario.distance,
                                            max_rounds=30, audit=True).run()
                            issues = audit_profiled_log(result.log, profiles, ruleset=ruleset)
                            issues.extend(audit_battle_result(result, profiles,
                                          expected_seed=seed, max_rounds=30))
                            issues.extend(audit_open_field_distance(result.log, scenario.distance))
                            self.assertEqual(issues, [])


if __name__ == '__main__':
    unittest.main()
