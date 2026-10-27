"""Independent golden cases from Core Rulebook pp. 12-15, 33-34.

Expected values below are frozen reference calculations, not calls to the engine.
This suite covers only d616 classification and basic damage, not complete combat.
"""

from collections import Counter
from itertools import product
import unittest

from blacklight.dice import DieRoll, classify
from blacklight.damage import calculate


EXPECTED_TOTAL_COUNTS = {
    4: 1, 5: 3, 6: 6, 7: 10, 8: 16, 9: 22, 10: 26,
    11: 28, 12: 28, 13: 26, 14: 20, 15: 14, 16: 9,
    17: 5, 18: 2,
}
EXPECTED_FANTASTIC_COUNTS = {
    8: 1, 9: 2, 10: 3, 11: 4, 12: 5, 13: 6,
    14: 5, 15: 4, 16: 3, 17: 2, 18: 1,
}


class TestDiceReference(unittest.TestCase):
    def test_exact_d616_distribution(self):
        totals = Counter()
        fantastic_totals = Counter()
        for left, marvel, right in product(range(1, 7), repeat=3):
            roll = DieRoll(left, marvel, right)
            totals[roll.total] += 1
            if roll.fantastic:
                fantastic_totals[roll.total] += 1
        self.assertEqual(dict(totals), EXPECTED_TOTAL_COUNTS)
        self.assertEqual(dict(fantastic_totals), EXPECTED_FANTASTIC_COUNTS)
        self.assertEqual(sum(totals.values()), 216)
        self.assertEqual(sum(fantastic_totals.values()), 36)

    def test_marvel_one_counts_as_six(self):
        self.assertEqual(DieRoll(1, 1, 1).total, 8)
        self.assertTrue(DieRoll(1, 1, 1).fantastic)
        self.assertEqual(DieRoll(6, 6, 6).total, 18)
        self.assertFalse(DieRoll(6, 6, 6).fantastic)

    def test_fantastic_success_and_failure(self):
        failure = classify(DieRoll(1, 1, 1), modifier=1, target=10)
        self.assertFalse(failure.success)
        self.assertTrue(failure.fantastic)
        self.assertFalse(failure.ultimate)
        success = classify(DieRoll(1, 1, 1), modifier=2, target=10)
        self.assertTrue(success.success)
        self.assertTrue(success.fantastic)
        self.assertFalse(success.ultimate)

    def test_ultimate_auto_success_beyond_numeric_max(self):
        ordinary_eighteen = classify(DieRoll(6, 6, 6), modifier=0, target=20)
        self.assertFalse(ordinary_eighteen.success)
        self.assertFalse(ordinary_eighteen.ultimate)
        ultimate = classify(DieRoll(6, 1, 6), modifier=0, target=20)
        self.assertTrue(ultimate.success)
        self.assertTrue(ultimate.fantastic)
        self.assertTrue(ultimate.ultimate)


class TestDamageReference(unittest.TestCase):
    def test_nonstacking_bonus_and_reduction(self):
        actual = calculate(
            marvel_face=4, base_rank=3, ability=6,
            bonus_candidates=[3, 2], reduction=1, fantastic=False,
        )
        self.assertEqual(actual, 26)

    def test_fantastic_doubles_after_reduction_and_ability(self):
        actual = calculate(
            marvel_face=1, base_rank=4, ability=3,
            bonus_candidates=[], reduction=2, fantastic=True,
        )
        self.assertEqual(actual, 30)

    def test_marvel_logo_damage_and_nonstacking_bonuses(self):
        actual = calculate(
            marvel_face=1, base_rank=3, ability=6,
            bonus_candidates=[3, 2], reduction=1, fantastic=True,
        )
        self.assertEqual(actual, 72)

    def test_reduction_to_zero_eliminates_ability_bonus_too(self):
        actual = calculate(
            marvel_face=6, base_rank=3, ability=6,
            bonus_candidates=[], reduction=3, fantastic=True,
        )
        self.assertEqual(actual, 0)

    def test_mighty_and_weapon_bonuses_do_not_stack(self):
        actual = calculate(
            marvel_face=4, base_rank=4, ability=5,
            bonus_candidates=[4, 1], reduction=2, fantastic=False,
        )
        self.assertEqual(actual, 29)


if __name__ == "__main__":
    unittest.main()
