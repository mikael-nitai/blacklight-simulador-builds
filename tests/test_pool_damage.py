"""Hand-calculated references for the later literal-dice house rule."""

import unittest

from experimental.pool_damage import roll_damage_pool


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

    def test_zero_dice_means_zero_damage_and_odd_bonus_requires_ruling(self):
        zero = roll_damage_pool(SequenceRNG([]), full_multiplier=3,
                                ability=6, reduction=3)
        self.assertEqual(zero.damage, 0)
        with self.assertRaises(ValueError):
            roll_damage_pool(SequenceRNG([]), full_multiplier=8,
                             ability=5, fast_strikes=True)


if __name__ == "__main__":
    unittest.main()
