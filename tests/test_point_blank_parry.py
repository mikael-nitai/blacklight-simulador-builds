from dataclasses import replace
import unittest

from experimental.point_blank_parry import ParryTrigger, point_blank_parry
from experimental.reaction_pools import start_round, spend_reaction


class PointBlankParryTests(unittest.TestCase):
    def setUp(self):
        self.trigger = ParryTrigger(True, 3, True, True, True, 2, 6, True, True, 1)
        self.reactions = start_round(combat_reflexes=False, fast_hands=True)

    def test_reaction_cost_and_pending_attack(self):
        result = point_blank_parry(self.trigger, self.reactions, pool='fast_hands')
        self.assertEqual((result.focus_after, result.reactions_after.ordinary,
                          result.reactions_after.fast_hands, result.ranged_attack_pending),
                         (1, 1, 0, True))

    def test_each_trigger_and_resource_requirement(self):
        changes = (dict(has_power=False), dict(rank=1), dict(enemy_attack=False),
                   dict(attack_missed=False), dict(target_was_user=False), dict(distance=3),
                   dict(focus=5), dict(has_ranged_weapon=False), dict(can_react=False))
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                point_blank_parry(replace(self.trigger, **change), self.reactions, pool='ordinary')

    def test_fast_hands_can_pay_after_ordinary_reaction_on_another_trigger(self):
        state = spend_reaction(self.reactions, pool='ordinary', trigger=2,
                               power_set='none', can_react=True)
        self.assertEqual(point_blank_parry(self.trigger, state, pool='fast_hands').focus_after, 1)
        with self.assertRaises(ValueError):
            point_blank_parry(replace(self.trigger, trigger=2), state, pool='fast_hands')

    def test_invalid_trigger_types_rejected(self):
        for change in (dict(distance=0), dict(focus=-1), dict(rank=True), dict(attack_missed=1)):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(self.trigger, **change)
