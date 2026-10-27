"""The independent log checker must detect arithmetic edits and bad ledgers."""

from dataclasses import replace
import unittest

from blacklight.audit import audit_log
from blacklight.engine import Duel, blacklight_profile
from blacklight.policies import BLADE_HAMMER_FAST, HAMMER


class TestAudit(unittest.TestCase):
    @staticmethod
    def battle(seed):
        a = blacklight_profile()
        b = replace(a, name="Enemy")
        return Duel((a, b), (BLADE_HAMMER_FAST, HAMMER), seed=seed,
                    audit=True).run()

    def test_short_complete_logs_are_self_consistent(self):
        for seed in range(100):
            result = self.battle(seed)
            self.assertEqual(audit_log(result.log,
                                       {"Blacklight": 150, "Enemy": 150},
                                       {"Blacklight": 90, "Enemy": 90}), [])

    def test_checker_rejects_corrupted_damage(self):
        result = self.battle(0)
        log = [dict(event) for event in result.log]
        attack = next(event for event in log if event["type"] == "attack"
                      and event["success"])
        attack["calculated_damage"] += 1
        issues = audit_log(log, {"Blacklight": 150, "Enemy": 150},
                           {"Blacklight": 90, "Enemy": 90})
        self.assertTrue(any("damage arithmetic mismatch" in issue for issue in issues))

    def test_checker_rejects_second_reaction_reset_in_same_round(self):
        result = self.battle(0)
        log = [dict(event) for event in result.log]
        reset = next(event for event in log if event["type"] == "reaction_reset")
        log.insert(log.index(reset) + 1, dict(reset))
        for seq, event in enumerate(log, 1):
            event["seq"] = seq
        issues = audit_log(log, {"Blacklight": 150, "Enemy": 150},
                           {"Blacklight": 90, "Enemy": 90})
        self.assertTrue(any("duplicate reaction reset" in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
