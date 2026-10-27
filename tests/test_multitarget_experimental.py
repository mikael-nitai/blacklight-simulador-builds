"""Independent hand-calculated oracles for the isolated two-target primitive."""

import unittest

from blacklight.dice import DieRoll
from experimental.multi_target import Target, resolve_fast_strikes


class SequenceRNG:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        value = next(self.values)
        assert low <= value <= high
        return value


class TestMultiTargetFastStrikes(unittest.TestCase):
    def test_one_roll_can_hit_one_defense_and_miss_the_other(self):
        # 4+2+5+6 = 17. Rank3+Mighty3-DR1 = 5; half = 2d6+3.
        outcomes = resolve_fast_strikes(
            DieRoll(4, 2, 5), SequenceRNG([2, 2]),
            melee_modifier=6, rank=3,
            damage_ability=6, bonus_candidates=(3,),
            targets=(Target("A", 16, 90, 1), Target("B", 20, 120, 0)))
        self.assertEqual([(o.target, o.success, o.damage, o.health_after)
                          for o in outcomes],
                         [("A", True, 7, 83), ("B", False, 0, 120)])

    def test_fantastic_is_full_per_target_after_own_reduction(self):
        # 5+M(6)+4+6 = 21; no fantastic doubling for Fast Strikes.
        # A: 6*(3+3-1)+6=36. B: 6*(3+3-3)+6=24.
        outcomes = resolve_fast_strikes(
            DieRoll(5, 1, 4), SequenceRNG([1] * 8),
            melee_modifier=6, rank=3,
            damage_ability=6, bonus_candidates=(3,),
            targets=(Target("A", 16, 90, 1), Target("B", 18, 120, 3)))
        self.assertEqual([(o.success, o.fantastic, o.damage)
                          for o in outcomes], [(True, True, 36),
                                                (True, True, 24)])

    def test_single_target_two_damage_components_and_rejects_duplicate_target(self):
        target = Target("A", 16, 90, 1)
        outcomes = resolve_fast_strikes(
            DieRoll(5, 1, 4), SequenceRNG([1] * 10),
            melee_modifier=6, rank=3,
            damage_ability=6, bonus_candidates=(3,), targets=(target,))
        self.assertEqual(len(outcomes), 1)
        self.assertEqual((outcomes[0].damage, len(outcomes[0].damage_faces)),
                         (72, 2))
        with self.assertRaises(ValueError):
            resolve_fast_strikes(
                DieRoll(5, 1, 4), SequenceRNG([]),
                melee_modifier=6, rank=3,
                damage_ability=6, bonus_candidates=(3,),
                targets=(target, target))


if __name__ == "__main__":
    unittest.main()
