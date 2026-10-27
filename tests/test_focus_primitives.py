"""Independent table oracles for the isolated Focus-damage primitive."""

import unittest

from blacklight.dice import DieRoll
from experimental.focus_primitives import resolve_mental_punch


def strike(roll: tuple[int, int, int], *, focus: int = 90,
           max_focus: int = 90, shield: int = 0,
           focus_dr: int = 0, heroic: bool = False,
           defense: int = 16):
    return resolve_mental_punch(
        DieRoll(*roll), attacker_rank=3, attacker_melee=6,
        target_melee_defense=defense, target_focus=focus,
        target_max_focus=max_focus, focus_reduction=focus_dr,
        shield_reduction=shield, attacker_heroic=heroic)


class TestFocusPrimitive(unittest.TestCase):
    def test_regular_focus_hit_and_explicit_shield_variant(self):
        unshielded = strike((3, 4, 3))  # total 16, 4*3+6 = 18
        shielded = strike((3, 4, 3), shield=2)  # 4*(3-2)+6 = 10
        self.assertEqual((unshielded.damage, unshielded.focus_after), (18, 72))
        self.assertEqual((shielded.damage, shielded.focus_after), (10, 80))
        self.assertFalse(shielded.stunned)

    def test_fantastic_doubles_and_stuns(self):
        result = strike((3, 1, 3), focus=50)
        self.assertEqual((result.total, result.damage, result.focus_after),
                         (18, 48, 2))  # 2*(6*3+6)
        self.assertTrue(result.stunned)
        self.assertEqual(strike((3, 1, 3), shield=2).damage, 24)

    def test_fantastic_failure_and_ultimate(self):
        failure = strike((1, 1, 1))  # 1+6+1+6=14 vs 16
        self.assertEqual((failure.damage, failure.stunned), (0, False))
        ultimate = strike((6, 1, 6), defense=50)
        self.assertEqual((ultimate.success, ultimate.damage,
                          ultimate.stunned), (True, 48, True))

    def test_focus_dr_can_zero_multiplier(self):
        result = strike((6, 1, 6), focus_dr=3)
        self.assertEqual((result.damage, result.focus_after), (0, 90))
        self.assertTrue(result.stunned)

    def test_demoralized_shattered_and_heroic_floor(self):
        zero = strike((3, 4, 3), focus=18)
        self.assertEqual(zero.focus_after, 0)
        self.assertTrue(zero.demoralized)
        self.assertFalse(zero.shattered)
        shattered = strike((3, 4, 3), focus=-72)
        self.assertEqual(shattered.focus_after, -90)
        self.assertTrue(shattered.shattered)
        spared = strike((3, 4, 3), focus=-80, heroic=True)
        self.assertEqual((spared.focus_after, spared.applied), (-89, 9))
        self.assertFalse(spared.shattered)

    def test_invalid_state_and_reduction(self):
        for options in ({"shield": 3}, {"focus_dr": -1},
                        {"focus": 91}, {"max_focus": 0}):
            with self.assertRaises(ValueError):
                strike((3, 4, 3), **options)


if __name__ == "__main__":
    unittest.main()
