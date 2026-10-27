"""Audit full traces across every preregistered policy and opponent."""

import unittest

from blacklight.audit import audit_log
from blacklight.engine import Duel, blacklight_profile
from blacklight.experiment import scenarios, seed_for, strategies


class TestCrossScenarioTraces(unittest.TestCase):
    def test_one_hundred_full_traces_per_cell(self):
        for scenario in scenarios():
            for strategy in strategies():
                profile = blacklight_profile()
                for index in range(100):
                    with self.subTest(scenario=scenario.id,
                                      strategy=strategy.id, index=index):
                        result = Duel(
                            (profile, scenario.opponent),
                            (strategy.policy, scenario.policy),
                            seed=seed_for("audit", scenario.id,
                                          strategy.id, index),
                            initial_distance=scenario.distance,
                            max_rounds=30, audit=True,
                        ).run()
                        issues = audit_log(
                            result.log,
                            {profile.name: profile.max_health,
                             scenario.opponent.name: scenario.opponent.max_health},
                            {profile.name: profile.max_focus,
                             scenario.opponent.name: scenario.opponent.max_focus},
                        )
                        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
