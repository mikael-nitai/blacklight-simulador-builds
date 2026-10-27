"""Independent group-log recalculation and mutation checks."""

from copy import deepcopy
from dataclasses import replace
import unittest

from blacklight.engine import blacklight_profile
from experimental.group import GroupBattle
from experimental.group_audit import audit_group_log, audit_group_result
from experimental.group_policies import (GROUP_ENEMY, GROUP_FAST,
                                         GROUP_HAMMER, GROUP_HAMMER_SHIELD)
from test_group_experimental import lower_enemy


class TestGroupAudit(unittest.TestCase):
    @staticmethod
    def profiles():
        return blacklight_profile(), lower_enemy("E1"), lower_enemy("E2")

    def test_three_policies_one_hundred_full_logs_each(self):
        profiles = self.profiles()
        for policy in (GROUP_HAMMER, GROUP_HAMMER_SHIELD, GROUP_FAST):
            for seed in range(100):
                result = GroupBattle(profiles,
                                     (policy, GROUP_ENEMY, GROUP_ENEMY),
                                     seed=seed, audit=True).run()
                self.assertEqual(audit_group_result(result, profiles), [],
                                 (policy.name, seed))

    def test_corrupted_damage_is_rejected(self):
        profiles = self.profiles()
        result = GroupBattle(profiles,
                             (GROUP_HAMMER, GROUP_ENEMY, GROUP_ENEMY),
                             seed=3, audit=True).run()
        log = deepcopy(list(result.log))
        target = next(e for e in log if e["type"] == "attack_target"
                      and e["success"])
        target["calculated_damage"] += 1
        issues = audit_group_log(log, profiles)
        self.assertTrue(any("damage arithmetic mismatch" in i for i in issues))

    def test_corrupted_damage_face_is_rejected(self):
        profiles = self.profiles()
        result = GroupBattle(profiles,
                             (GROUP_HAMMER, GROUP_ENEMY, GROUP_ENEMY),
                             seed=3, audit=True).run()
        log = deepcopy(list(result.log))
        target = next(e for e in log if e["type"] == "attack_target"
                      and e["damage_faces"])
        target["damage_faces"][0][0] = 7
        issues = audit_group_log(log, profiles)
        self.assertTrue(any("damage dice ledger mismatch" in i for i in issues))

    def test_duplicate_reaction_reset_is_rejected(self):
        profiles = self.profiles()
        result = GroupBattle(profiles,
                             (GROUP_HAMMER_SHIELD, GROUP_ENEMY, GROUP_ENEMY),
                             seed=3, audit=True).run()
        log = deepcopy(list(result.log))
        reset = next(e for e in log if e["type"] == "reaction_reset")
        log.insert(log.index(reset) + 1, deepcopy(reset))
        for seq, event in enumerate(log, 1):
            event["seq"] = seq
        issues = audit_group_log(log, profiles)
        self.assertTrue(any("duplicate reaction reset" in i for i in issues))

    def test_incorrect_applied_damage_and_terminal_state_are_rejected(self):
        profiles = self.profiles()
        result = GroupBattle(profiles,
                             (GROUP_HAMMER, GROUP_ENEMY, GROUP_ENEMY),
                             seed=3, audit=True).run()
        log = deepcopy(list(result.log))
        target = next(e for e in log if e["type"] == "attack_target"
                      and e["success"])
        target["health_after"] += 1
        target["damage"] -= 1
        issues = audit_group_log(log, profiles)
        self.assertTrue(any("applied damage mismatch" in i for i in issues))
        corrupted = replace(result, final_health=(999, *result.final_health[1:]))
        self.assertIn("final Health mismatch",
                      audit_group_result(corrupted, profiles))


if __name__ == "__main__":
    unittest.main()
