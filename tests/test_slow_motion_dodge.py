import unittest
from dataclasses import replace

from experimental.slow_motion_dodge import (DodgeTrigger, can_use_slow_motion_dodge,
                                            resolve_slow_motion_dodge)


class SlowMotionDodgeContractTests(unittest.TestCase):
    def setUp(self):
        self.trigger = DodgeTrigger(True, True, 'agility', True, True, 2, False)

    def test_activation_spends_one_reaction_and_adds_one_trouble(self):
        self.assertTrue(can_use_slow_motion_dodge(self.trigger))
        outcome = resolve_slow_motion_dodge(self.trigger, activate=True)
        self.assertEqual((outcome.activated, outcome.reactions_remaining,
                          outcome.added_troubles, outcome.reacted_to_trigger),
                         (True, 1, 1, True))

    def test_declining_preserves_resources(self):
        outcome = resolve_slow_motion_dodge(self.trigger, activate=False)
        self.assertEqual((outcome.activated, outcome.reactions_remaining,
                          outcome.added_troubles, outcome.reacted_to_trigger),
                         (False, 2, 0, False))

    def test_every_gate_is_required_and_failed_activation_is_rejected(self):
        variations = (dict(has_power=False), dict(enemy_attack=False), dict(defense='melee'),
                      dict(before_roll=False), dict(can_react=False),
                      dict(reactions_remaining=0), dict(already_reacted=True))
        for change in variations:
            with self.subTest(change=change):
                trigger = replace(self.trigger, **change)
                self.assertFalse(can_use_slow_motion_dodge(trigger))
                with self.assertRaises(ValueError):
                    resolve_slow_motion_dodge(trigger, activate=True)
                outcome = resolve_slow_motion_dodge(trigger, activate=False)
                self.assertEqual(outcome.reactions_remaining, trigger.reactions_remaining)
                self.assertEqual(outcome.reacted_to_trigger, trigger.already_reacted)

    def test_a_new_trigger_can_consume_another_reaction(self):
        first = resolve_slow_motion_dodge(self.trigger, activate=True)
        new_trigger = replace(self.trigger, reactions_remaining=first.reactions_remaining)
        second = resolve_slow_motion_dodge(new_trigger, activate=True)
        self.assertEqual(second.reactions_remaining, 0)
        self.assertFalse(can_use_slow_motion_dodge(replace(new_trigger, reactions_remaining=0)))

    def test_bad_context_is_rejected_instead_of_coerced(self):
        for change in (dict(reactions_remaining=-1), dict(reactions_remaining=True),
                       dict(before_roll=1), dict(defense='ranged')):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(self.trigger, **change)
        with self.assertRaises(ValueError):
            resolve_slow_motion_dodge(self.trigger, activate=1)
        with self.assertRaises(ValueError):
            can_use_slow_motion_dodge(None)


if __name__ == '__main__':
    unittest.main()
