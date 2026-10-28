"""Explicit revision checks use declared contracts, not the motor's label."""

from copy import deepcopy
import unittest

from blacklight.ruleset_audit import audit_ruleset_log
from blacklight.rulesets import CURRENT_RULESET, LEGACY_RULESET


def attack(*, current=False, fast=True):
    event = {'seq': 1, 'type': 'attack', 'mode': 'hammer_fast' if fast else 'hammer',
             'damage_model': 'literal_marvel_pool_v2', 'fantastic': False,
             'damage_denominator': 2 if fast else 1,
             'default_fantastic_multiplier': not fast}
    if current and fast:
        event.update(fast_use_id=1, fast_zero_dice_bonus=True)
    return event


class TestRulesetAudit(unittest.TestCase):
    def test_old_and_new_fast_are_distinct_but_ordinary_attacks_remain_compatible(self):
        old, new, regular = attack(), attack(current=True), attack(fast=False)
        self.assertEqual(audit_ruleset_log([old], LEGACY_RULESET), [])
        self.assertEqual(audit_ruleset_log([new], CURRENT_RULESET), [])
        self.assertTrue(audit_ruleset_log([old], CURRENT_RULESET))
        self.assertTrue(audit_ruleset_log([new], LEGACY_RULESET))
        self.assertEqual(audit_ruleset_log([regular], LEGACY_RULESET), [])
        self.assertEqual(audit_ruleset_log([regular], CURRENT_RULESET), [])

    def test_unknown_models_revisions_and_forged_event_conventions_fail(self):
        original = attack(current=True)
        for key, value in (('damage_model', 'unknown'), ('fast_zero_dice_bonus', False),
                           ('damage_denominator', 1), ('default_fantastic_multiplier', True)):
            modified = deepcopy(original)
            modified[key] = value
            with self.subTest(key=key):
                self.assertTrue(audit_ruleset_log([modified], CURRENT_RULESET))
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            audit_ruleset_log([original], 'future_unknown_ruleset')


if __name__ == '__main__':
    unittest.main()
