"""Forced wall geometry and complete-trace audit for the corridor gate."""

from copy import deepcopy
from dataclasses import replace
import unittest

from blacklight.audit import audit_log
from blacklight.engine import Move, blacklight_profile
from blacklight.experiment import scenarios
from blacklight.policies import HAMMER, KITER, SHIELD_HAMMER_REACTIVE
from experimental.corridor import CorridorDuel
from experimental.corridor_audit import audit_corridor


class SequenceRNG:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        value = next(self.values)
        assert low <= value <= high
        return value


def gunner(*, ammunition=True):
    original = next(s.opponent for s in scenarios()
                    if s.id == "gunner_kiter")
    return original if ammunition else replace(
        original, rank=4, ranged_is_ammunition=False)


def game(*, length=12, ammunition=True,
         policy=HAMMER, seed=1, audit=True):
    return CorridorDuel(
        (blacklight_profile(), gunner(ammunition=ammunition)),
        (policy, KITER), seed=seed, length=length,
        initial_positions=(0, 8), audit=audit)


class TestCorridor(unittest.TestCase):
    def test_wall_caps_retreat_and_updates_distance(self):
        duel = game()
        duel.round = 1
        duel.active_actor = 1
        duel.fighters[1].movement_available = True
        duel._move(1, Move("retreat", 6))
        self.assertEqual((duel.positions, duel.distance), ([0, 12], 12))
        self.assertEqual(duel.log[-1]["actual_steps"], 4)
        duel.fighters[1].movement_available = True
        duel._move(1, Move("retreat", 6))
        self.assertEqual(duel.log[-1]["actual_steps"], 0)
        duel.active_actor = 0
        duel.fighters[0].movement_available = True
        duel._move(0, Move("approach", 5))
        self.assertEqual((duel.positions, duel.distance), ([5, 12], 7))
        self.assertEqual(audit_corridor(
            duel.log, tuple(f.profile.name for f in duel.fighters),
            initial_positions=(0, 8), length=12,
            final_positions=tuple(duel.positions)), [])

    def test_cannot_cross_or_leave_corridor(self):
        duel = game(length=8)
        duel.round = 1
        duel.active_actor = 0
        duel.fighters[0].movement_available = True
        duel._move(0, Move("approach", 5))
        self.assertEqual(duel.positions, [5, 8])
        duel.fighters[0].movement_available = True
        duel._move(0, Move("approach", 5))
        self.assertEqual(duel.positions, [7, 8])
        self.assertEqual(duel.distance, 1)

    def test_reproducibility_and_four_hundred_complete_audits(self):
        for length in (12, 20):
            for ammunition in (True, False):
                for seed in range(100):
                    duel = game(length=length, ammunition=ammunition,
                                policy=SHIELD_HAMMER_REACTIVE,
                                seed=seed)
                    result = duel.run()
                    profiles = tuple(f.profile for f in duel.fighters)
                    self.assertEqual(audit_log(
                        result.log,
                        {p.name: p.max_health for p in profiles},
                        {p.name: p.max_focus for p in profiles}), [],
                        (length, ammunition, seed, "combat"))
                    self.assertEqual(audit_corridor(
                        result.log, tuple(p.name for p in profiles),
                        initial_positions=(0, 8), length=length,
                        final_positions=tuple(duel.positions)), [],
                        (length, ammunition, seed, "positions"))
        a = game(seed=41).run()
        b = game(seed=41).run()
        self.assertEqual(a, b)

    def test_corrupted_position_trace_is_rejected(self):
        duel = game(seed=2)
        result = duel.run()
        log = deepcopy(list(result.log))
        movement = next(e for e in log if e["type"] == "movement"
                        and e["actual_steps"] > 0)
        movement["distance_after"] += 1
        issues = audit_corridor(
            log, tuple(f.profile.name for f in duel.fighters),
            initial_positions=(0, 8),
            length=12, final_positions=tuple(duel.positions))
        self.assertTrue(any("position ledger mismatch" in x for x in issues))

    def test_unmodeled_knockback_stops_corridor_combat(self):
        duel = game(policy=replace(HAMMER, edge_mode="decline"))
        duel.positions = [7, 8]
        duel.distance = 1
        duel.fighters[1].stance = True
        duel.rng = SequenceRNG([6, 1, 6])
        with self.assertRaises(NotImplementedError):
            duel._attack(0, "hammer")


if __name__ == "__main__":
    unittest.main()
