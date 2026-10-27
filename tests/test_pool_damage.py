"""Hand-calculated references for the later literal-dice house rule."""

import unittest
from collections import Counter
from itertools import product
from random import Random

from blacklight.pool_damage import roll_damage_pool


class SequenceRNG:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        value = next(self.values)
        assert low <= value <= high
        return value


class TestPoolDamage(unittest.TestCase):
    def test_every_damage_die_uses_marvel_one_as_six(self):
        result = roll_damage_pool(SequenceRNG([1, 2, 3, 4, 5, 6]),
                                  full_multiplier=6, ability=6)
        self.assertEqual(result.faces, (1, 2, 3, 4, 5, 6))
        self.assertEqual(result.damage, 32)  # 6+2+3+4+5+6 + ability 6
        self.assertEqual(result.dice_rolled, 6)

    def test_normal_fantastic_doubles_total_after_rolling(self):
        result = roll_damage_pool(SequenceRNG([1] * 8),
                                  full_multiplier=8, ability=6,
                                  fantastic=True)
        self.assertEqual(result.damage, 108)  # 2 * (8*6+6)

    def test_fast_hammer_blade_common_is_seven_dice_plus_six(self):
        rng = SequenceRNG([1] * 7)
        hammer = roll_damage_pool(rng, full_multiplier=8, ability=6,
                                  fast_strikes=True)
        blade = roll_damage_pool(rng, full_multiplier=7, ability=6,
                                 fast_strikes=True)
        self.assertEqual((hammer.dice_rolled, hammer.ability_added), (4, 3))
        self.assertEqual((blade.dice_rolled, blade.ability_added), (3, 3))
        self.assertEqual(hammer.damage + blade.damage, 48)  # 7*6+6

    def test_fast_fantastic_uses_full_two_components(self):
        rng = SequenceRNG([1] * 15)
        hammer = roll_damage_pool(rng, full_multiplier=8, ability=6,
                                  fast_strikes=True, fantastic=True)
        blade = roll_damage_pool(rng, full_multiplier=7, ability=6,
                                 fast_strikes=True, fantastic=True)
        self.assertEqual((hammer.dice_rolled, blade.dice_rolled), (8, 7))
        self.assertEqual(hammer.damage + blade.damage, 102)  # 15*6+12

    def test_damage_reduction_precedes_fast_halving(self):
        rng = SequenceRNG([6] * 4)
        hammer = roll_damage_pool(rng, full_multiplier=8, ability=6,
                                  reduction=3, fast_strikes=True)
        blade = roll_damage_pool(rng, full_multiplier=7, ability=6,
                                 reduction=3, fast_strikes=True)
        self.assertEqual((hammer.dice_rolled, blade.dice_rolled), (2, 2))
        self.assertEqual(hammer.damage + blade.damage, 30)

    def test_counterfactual_dice_are_separate_from_applied_dice(self):
        result = roll_damage_pool(
            SequenceRNG([1, 2, 3, 4]), full_multiplier=8,
            ability=6, reduction=3, fast_strikes=True,
            sample_counterfactual=True)
        self.assertEqual(result.faces, (1, 2))
        self.assertEqual(result.counterfactual_faces, (3, 4))
        self.assertEqual(result.damage, 11)  # 6+2+3
        self.assertEqual(result.damage_without_reduction, 18)  # 6+2+3+4+3

    def test_zero_dice_means_zero_damage_and_odd_bonus_requires_ruling(self):
        zero = roll_damage_pool(SequenceRNG([]), full_multiplier=3,
                                ability=6, reduction=3)
        self.assertEqual(zero.damage, 0)
        with self.assertRaises(ValueError):
            roll_damage_pool(SequenceRNG([]), full_multiplier=8,
                             ability=5, fast_strikes=True)

    def test_fast_halving_zero_dice_keeps_ability_after_positive_dr_remainder(self):
        result = roll_damage_pool(SequenceRNG([]), full_multiplier=3,
                                  ability=6, reduction=2, fast_strikes=True)
        self.assertEqual((result.dice_after_reduction, result.dice_rolled,
                          result.ability_added, result.faces, result.damage),
                         (1, 0, 3, (), 3))

    def test_fast_dr_zero_still_removes_ability(self):
        for reduction in (3, 4):
            result = roll_damage_pool(SequenceRNG([]), full_multiplier=3,
                                      ability=6, reduction=reduction, fast_strikes=True)
            self.assertEqual((result.dice_rolled, result.ability_added, result.damage), (0, 0, 0))

    def test_zero_dice_counterfactual_keeps_bonus_without_reusing_hit_die(self):
        result = roll_damage_pool(SequenceRNG([]), full_multiplier=1,
                                  ability=6, fast_strikes=True,
                                  sample_counterfactual=True)
        self.assertEqual((result.damage, result.damage_without_reduction,
                          result.faces, result.counterfactual_faces), (3, 3, (), ()))
        prevented = roll_damage_pool(SequenceRNG([]), full_multiplier=1,
                                     ability=6, reduction=1, fast_strikes=True,
                                     sample_counterfactual=True)
        self.assertEqual((prevented.damage, prevented.damage_without_reduction), (0, 3))

    def test_historical_damage_convention_remains_reproducible(self):
        result = roll_damage_pool(SequenceRNG([]), full_multiplier=1, ability=6,
                                  fast_strikes=True, sample_counterfactual=True,
                                  fast_zero_dice_bonus=False)
        self.assertEqual((result.damage, result.ability_added, result.damage_without_reduction), (0, 0, 0))

    def test_exact_two_die_distribution_matches_enumeration(self):
        observed = Counter()
        expected = Counter()
        face_values = (6, 2, 3, 4, 5, 6)
        for first, second in product(range(1, 7), repeat=2):
            actual = roll_damage_pool(SequenceRNG([first, second]),
                                      full_multiplier=2, ability=0)
            observed[actual.damage] += 1
            expected[face_values[first - 1] + face_values[second - 1]] += 1
        self.assertEqual(observed, expected)
        self.assertEqual(sum(observed.values()), 36)

    def test_large_pool_mean_matches_exact_mean(self):
        rng = Random(4187)
        sample = [roll_damage_pool(rng, full_multiplier=6, ability=6).damage
                  for _ in range(50_000)]
        self.assertAlmostEqual(sum(sample) / len(sample), 6 * (26 / 6) + 6,
                               delta=0.08)


if __name__ == "__main__":
    unittest.main()
