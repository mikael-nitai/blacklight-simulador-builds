"""Forced check for the table-confirmed double edge on Fast Strikes."""

from dataclasses import replace
import unittest

from blacklight.engine import Duel, blacklight_profile
from blacklight.experiment import scenarios
from blacklight.policies import BLADE_HAMMER_FAST, ATTACK


class SequenceRNG:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        value = next(self.values)
        assert low <= value <= high
        return value


class TestFastRulingEdges(unittest.TestCase):
    def test_blazing_and_signature_both_reroll_on_one_attack_check(self):
        opponent = next(s.opponent for s in scenarios()
                        if s.id == "mirror_attack")
        duel = Duel(
            (blacklight_profile(), opponent),
            (replace(BLADE_HAMMER_FAST, edge_mode="marvel"), ATTACK),
            seed=1, stack_signature_edge=True, audit=True)
        duel.rng = SequenceRNG([3, 4, 3, 1, 6])
        duel._attack(0, "blade_fast", offhand="hammer")
        attacks = [event for event in duel.log
                   if event["type"] == "attack"]
        self.assertEqual(len(attacks), 1)
        self.assertEqual(attacks[0]["edges"], 2)
        self.assertEqual(len(attacks[0]["rerolls"]), 2)
        self.assertEqual(attacks[0]["roll"], [3, 1, 3])


if __name__ == "__main__":
    unittest.main()
