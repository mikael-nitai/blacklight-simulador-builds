"""Forced two-weapon pool attacks and independent trace rejection."""

from copy import deepcopy
from dataclasses import replace
import unittest

from blacklight.audit import audit_log
from blacklight.engine import Duel, blacklight_profile
from blacklight.policies import ATTACK, BLADE_HAMMER_FAST


class SequenceRNG:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        value = next(self.values)
        assert low <= value <= high
        return value


def duel(*, shield=False):
    victor = blacklight_profile()
    mirror = replace(victor, name="Mirror", shield_active=shield)
    game = Duel((victor, mirror),
                (replace(BLADE_HAMMER_FAST, edge_mode="decline"), ATTACK),
                seed=7, audit=True)
    return game, (victor, mirror)


class TestPoolIntegration(unittest.TestCase):
    def test_fast_common_separate_dr_then_halving(self):
        game, profiles = duel(shield=True)
        game.rng = SequenceRNG([6, 6, 6])
        game.damage_rng = SequenceRNG([1] * 30)
        game._attack(0, "blade_fast", offhand="hammer")
        event = next(x for x in game.log if x["type"] == "attack")
        self.assertEqual(event["edges"], 2)
        self.assertEqual(event["reduction"], 3)
        self.assertEqual([(x["weapon"], x["full_multiplier"],
                           x["dice_rolled"], x["ability_added"], x["damage"])
                          for x in event["damage_components"]],
                         [("blade", 7, 2, 3, 15),
                          ("hammer", 8, 2, 3, 15)])
        self.assertEqual(game.fighters[1].health, 120)
        self.assertEqual(audit_log(
            game.log, {p.name: p.max_health for p in profiles},
            {p.name: p.max_focus for p in profiles}), [])

    def test_fast_fantastic_two_full_components_and_effects(self):
        game, profiles = duel()
        game.rng = SequenceRNG([6, 1, 6])
        game.damage_rng = SequenceRNG([1] * 30)
        game._attack(0, "blade_fast", offhand="hammer")
        event = next(x for x in game.log if x["type"] == "attack")
        self.assertEqual([(x["dice_rolled"], x["damage"])
                          for x in event["damage_components"]],
                         [(6, 42), (7, 48)])
        self.assertEqual((game.fighters[1].health,
                          game.fighters[1].bleeding,
                          game.fighters[1].stunned_by), (60, 5, 0))
        self.assertEqual(audit_log(
            game.log, {p.name: p.max_health for p in profiles},
            {p.name: p.max_focus for p in profiles}), [])

    def test_auditor_rejects_modified_damage_face(self):
        game, profiles = duel()
        game.rng = SequenceRNG([6, 1, 6])
        game.damage_rng = SequenceRNG([1] * 30)
        game._attack(0, "blade_fast", offhand="hammer")
        changed = deepcopy(game.log)
        attack = next(x for x in changed if x["type"] == "attack")
        attack["damage_components"][0]["faces"][0] = 2
        issues = audit_log(
            changed, {p.name: p.max_health for p in profiles},
            {p.name: p.max_focus for p in profiles})
        self.assertTrue(any("component damage mismatch" in issue
                            for issue in issues))

    def test_auditor_rejects_modified_counterfactual_face(self):
        game, profiles = duel(shield=True)
        game.rng = SequenceRNG([6, 6, 6])
        game.damage_rng = SequenceRNG([1] * 30)
        game._attack(0, "blade_fast", offhand="hammer")
        changed = deepcopy(game.log)
        attack = next(x for x in changed if x["type"] == "attack")
        component = next(x for x in attack["damage_components"]
                         if x["counterfactual_faces"])
        component["counterfactual_faces"][0] = 2
        issues = audit_log(
            changed, {p.name: p.max_health for p in profiles},
            {p.name: p.max_focus for p in profiles})
        self.assertTrue(any("counterfactual damage mismatch" in issue
                            for issue in issues))


if __name__ == "__main__":
    unittest.main()
