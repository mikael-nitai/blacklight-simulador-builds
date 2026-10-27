"""Forced Focus-duel transitions plus independent complete-log audit."""

from copy import deepcopy
from dataclasses import replace
import unittest

from blacklight.engine import Profile, blacklight_profile
from experimental.focus_audit import audit_focus_duel
from experimental.focus_duel import FocusDuel, STRATEGIES


class SequenceRNG:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        value = next(self.values)
        assert low <= value <= high
        return value


def mentalist(rank: int = 3) -> Profile:
    return Profile("Mentalist", rank, 150, 60, 6, 1, 5, 2,
                   16, 11, 5, powers=frozenset({"mental_punch"}))


def game(*, strategy="hammer", reduction=0, seed=1):
    return FocusDuel(blacklight_profile(), mentalist(),
                     strategy=strategy, shield_focus_reduction=reduction,
                     seed=seed, audit=True)


class TestFocusDuel(unittest.TestCase):
    def test_shield_after_hit_changes_same_focus_attack_only_in_f2(self):
        protected = game(strategy="shield_reactive", reduction=2)
        protected.round = 1
        protected._reset_reactions()
        protected.rng = SequenceRNG([3, 4, 3])
        protected.damage_rng = SequenceRNG([4] * 30)
        protected._mental_punch()
        self.assertEqual(protected.fighters[0].focus, 80)
        self.assertEqual(protected.fighters[0].reactions, 1)
        self.assertTrue(protected.fighters[0].shield_active)
        kinds = [e["type"] for e in protected.log]
        self.assertLess(kinds.index("shield_activate"),
                        kinds.index("attack_target"))
        no_focus_protection = game(strategy="shield_reactive", reduction=0)
        no_focus_protection.round = 1
        no_focus_protection._reset_reactions()
        no_focus_protection.rng = SequenceRNG([3, 4, 3])
        no_focus_protection.damage_rng = SequenceRNG([4] * 30)
        no_focus_protection._mental_punch()
        self.assertEqual(no_focus_protection.fighters[0].focus, 72)

    def test_fantastic_mental_punch_stuns_and_next_turn_skips(self):
        battle = game()
        battle.round = 1
        battle.turn_counts[1] = 1
        battle.rng = SequenceRNG([3, 1, 3, 4, 4, 4])
        battle.damage_rng = SequenceRNG([1] * 30)
        battle._mental_punch()
        self.assertEqual(battle.fighters[0].focus, 42)
        self.assertEqual(battle.fighters[0].stunned_by, 1)
        battle._turn(0)
        self.assertTrue(any(e["type"] == "turn_skipped" for e in battle.log))
        battle._turn(1)
        self.assertIsNone(battle.fighters[0].stunned_by)

    def test_demoralized_cancels_blazing_edge(self):
        battle = game()
        battle.round = 1
        battle.fighters[0].focus = 0
        battle.rng = SequenceRNG([3, 4, 3])
        battle.damage_rng = SequenceRNG([4] * 30)
        battle._hammer()
        check = next(e for e in battle.log if e["type"] == "attack_check")
        self.assertEqual((check["edges"], check["troubles"]), (1, 1))
        self.assertEqual(battle.fighters[1].health, 112)

    def test_riposte_uses_reaction_after_mental_miss(self):
        victor = replace(blacklight_profile(),
                         powers=blacklight_profile().powers -
                         {"blazing_fast_fists"})
        battle = FocusDuel(victor, mentalist(), strategy="hammer",
                           shield_focus_reduction=0, seed=1, audit=True)
        battle.round = 1
        battle._reset_reactions()
        battle.rng = SequenceRNG([1, 2, 1, 3, 4, 4])
        battle.damage_rng = SequenceRNG([4] * 30)
        battle._mental_punch()
        self.assertEqual(battle.fighters[0].focus, 90)
        self.assertEqual(battle.fighters[0].reactions, 1)
        self.assertTrue(any(e["type"] == "attack_check" and e["reaction"]
                            for e in battle.log))

    def test_seed_replay_and_three_hundred_full_audits(self):
        profiles = (blacklight_profile(), mentalist())
        for strategy in STRATEGIES:
            for reduction in (0, 2):
                for seed in range(50):
                    battle = FocusDuel(*profiles, strategy=strategy,
                                       shield_focus_reduction=reduction,
                                       seed=seed, audit=True)
                    result = battle.run()
                    self.assertEqual(audit_focus_duel(result, profiles,
                                                      reduction), [],
                                     (strategy, reduction, seed))
        first = game(seed=41).run()
        second = game(seed=41).run()
        self.assertEqual(first, second)

    def test_auditor_rejects_changed_focus_damage_and_final_state(self):
        profiles = (blacklight_profile(), mentalist())
        result = game(seed=3).run()
        log = deepcopy(list(result.log))
        target = next(e for e in log if e["type"] == "attack_target"
                      and e["kind"] == "mental_punch" and e["applied"] > 0)
        target["calculated_damage"] += 1
        corrupted = replace(result, log=tuple(log))
        issues = audit_focus_duel(corrupted, profiles, 0)
        self.assertTrue(any("damage arithmetic mismatch" in x for x in issues))
        corrupted_final = replace(result, final_focus=(999, result.final_focus[1]))
        self.assertIn("final Focus mismatch",
                      audit_focus_duel(corrupted_final, profiles, 0))

    def test_auditor_rejects_changed_focus_damage_die(self):
        profiles = (blacklight_profile(), mentalist())
        result = game(seed=3).run()
        log = deepcopy(list(result.log))
        target = next(e for e in log if e["type"] == "attack_target"
                      and e["kind"] == "mental_punch" and e["damage_faces"])
        target["damage_faces"][0] = 7
        issues = audit_focus_duel(replace(result, log=tuple(log)), profiles, 0)
        self.assertTrue(any("invalid damage die face" in x for x in issues))


if __name__ == "__main__":
    unittest.main()
