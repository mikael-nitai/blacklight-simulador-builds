"""Forced oracles for the isolated fixed-contact group engine."""

from dataclasses import replace
import unittest

from blacklight.engine import Profile, blacklight_profile
from experimental.group import GroupBattle, IllegalGroupAction
from experimental.group_policies import (GROUP_ENEMY, GROUP_FAST,
                                         GROUP_HAMMER_SHIELD, GroupAction,
                                         GroupPolicy)


class SequenceRNG:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        result = next(self.values)
        assert low <= result <= high
        return result


class NoEdgeGroupPolicy(GroupPolicy):
    def choose_edge_die(self, *_):
        return None


def lower_enemy(name: str, *, melee: int = 4,
                resilience: int = 3, rank: int = 2) -> Profile:
    return Profile(name, rank=rank, max_health=30 * resilience,
                   max_focus=60, melee=melee, agility=1,
                   resilience=resilience, vigilance=2,
                   melee_defense=10 + melee, agility_defense=11,
                   run_speed=5)


class TestGroupPrototype(unittest.TestCase):
    def test_single_target_fast_uses_two_pools_and_two_edges(self):
        game = GroupBattle(
            (blacklight_profile(), lower_enemy("E1"), lower_enemy("E2")),
            (NoEdgeGroupPolicy("fast", preferred="fast_strikes"),
             GROUP_ENEMY, GROUP_ENEMY), seed=1, audit=True)
        game.round = 1
        game._reset_reactions()
        game.rng = SequenceRNG([6, 6, 6])
        game.damage_rng = SequenceRNG([1] * 30)
        game._attack(0, GroupAction("fast_strikes", (1,)))
        check = next(e for e in game.log if e["type"] == "attack_check")
        target = next(e for e in game.log if e["type"] == "attack_target")
        self.assertEqual(check["edges"], 2)
        self.assertEqual((target["calculated_damage"],
                          [len(faces) for faces in target["damage_faces"]]),
                         (42, [3, 3]))
        self.assertEqual(game.fighters[1].health, 48)

    def test_fixed_seed_replays_three_actor_log(self):
        profiles = (blacklight_profile(), lower_enemy("E1"),
                    lower_enemy("E2"))
        policies = (GROUP_HAMMER_SHIELD, GROUP_ENEMY, GROUP_ENEMY)
        a = GroupBattle(profiles, policies, seed=41, max_rounds=10,
                        audit=True).run()
        b = GroupBattle(profiles, policies, seed=41, max_rounds=10,
                        audit=True).run()
        self.assertEqual(a, b)
        self.assertIn(a.outcome, ("win", "loss", "inconclusive"))
        self.assertLessEqual(a.rounds, 10)
        self.assertTrue(any(e["type"] == "attack_check" for e in a.log))

    def test_fast_strikes_one_roll_two_defenses_one_standard_action(self):
        player = replace(blacklight_profile(),
                         powers=blacklight_profile().powers -
                         {"blazing_fast_fists"})
        game = GroupBattle(
            (player, lower_enemy("E1"), lower_enemy("E2", melee=6)),
            (NoEdgeGroupPolicy("fast", preferred="fast_strikes"),
             GROUP_ENEMY, GROUP_ENEMY), seed=1, audit=True)
        game.round = 1
        game._reset_reactions()
        game.active_actor = 0
        game.fighters[0].standard_available = True
        self.assertIn(GroupAction("fast_strikes", (1, 2)),
                      game.legal_actions(0))
        game.rng = SequenceRNG([3, 3, 3])  # total 15 vs defenses 14 and 16
        game.damage_rng = SequenceRNG([3] * 20)
        game._attack(0, GroupAction("fast_strikes", (1, 2)))
        self.assertEqual((game.fighters[1].health, game.fighters[2].health),
                         (78, 90))  # ceil((3*6+6)/2) = 12 vs E1 only
        checks = [e for e in game.log if e["type"] == "attack_check"]
        targets = [e for e in game.log if e["type"] == "attack_target"]
        self.assertEqual(len(checks), 1)
        self.assertEqual([(e["success"], e["damage"]) for e in targets],
                         [(True, 12), (False, 0)])
        self.assertEqual({e["trigger"] for e in targets}, {checks[0]["trigger"]})

    def test_shield_reaction_after_hit_protects_same_attack(self):
        attacker = lower_enemy("E1", rank=4)
        game = GroupBattle(
            (blacklight_profile(), attacker, lower_enemy("E2")),
            (GROUP_HAMMER_SHIELD, GROUP_ENEMY, GROUP_ENEMY),
            seed=1, audit=True)
        game.round = 1
        game._reset_reactions()
        game.rng = SequenceRNG([4, 4, 4])  # 16 vs Victor defense 16
        game.damage_rng = SequenceRNG([4] * 20)
        game._attack(1, GroupAction("melee", (0,)))
        self.assertEqual(game.fighters[0].health, 142)
        self.assertEqual(game.fighters[0].reactions, 1)
        self.assertTrue(game.fighters[0].shield_active)
        kinds = [e["type"] for e in game.log]
        self.assertLess(kinds.index("shield_activate"),
                        kinds.index("attack_target"))
        target = next(e for e in game.log if e["type"] == "attack_target")
        self.assertEqual(target["reduction"], 3)

    def test_two_reactions_shared_across_distinct_misses(self):
        game = GroupBattle(
            (blacklight_profile(), lower_enemy("E1"), lower_enemy("E2")),
            (NoEdgeGroupPolicy("hammer", preferred="hammer"),
             GROUP_ENEMY, GROUP_ENEMY), seed=1, audit=True)
        game.round = 1
        game._reset_reactions()
        game.rng = SequenceRNG([
            1, 2, 1, 3, 4, 4,  # E1 misses, Victor Ripostes E1
            1, 2, 1, 3, 4, 4,  # E2 misses, Victor Ripostes E2
            1, 2, 1,           # E1 misses again; no reaction remains
        ])
        for actor in (1, 2, 1):
            game._attack(actor, GroupAction("melee", (0,)))
            game._drain_reactions()
        self.assertEqual(game.fighters[0].reactions, 0)
        self.assertEqual(sum(e["type"] == "reaction_spent"
                             and e["actor"] == "Blacklight"
                             for e in game.log), 2)

    def test_stunned_expires_at_start_of_source_next_turn(self):
        game = GroupBattle(
            (blacklight_profile(), lower_enemy("E1", resilience=6),
             lower_enemy("E2")),
            (NoEdgeGroupPolicy("hammer", preferred="hammer"),
             GROUP_ENEMY, GROUP_ENEMY), seed=1, audit=True)
        game.round = 1
        game.turn_counts[0] = 1
        game.rng = SequenceRNG([5, 1, 4, 2, 2, 2])
        game.damage_rng = SequenceRNG([6] * 30)
        game._attack(0, GroupAction("hammer", (1,)))
        self.assertEqual(game.fighters[1].health, 72)
        self.assertEqual(game.fighters[1].stunned_by, 0)
        game._turn(1)
        self.assertTrue(any(e["type"] == "turn_skipped"
                            and e["actor"] == "E1" for e in game.log))
        game._turn(0)
        self.assertIsNone(game.fighters[1].stunned_by)
        self.assertTrue(any(e["type"] == "condition_end"
                            and e["actor"] == "E1" for e in game.log))

    def test_bonus_round_eligibility_and_illegal_group_target(self):
        game = GroupBattle(
            (blacklight_profile(), lower_enemy("E1"), lower_enemy("E2")),
            (NoEdgeGroupPolicy("hammer", preferred="hammer"),
             GROUP_ENEMY, GROUP_ENEMY), seed=1, audit=True)
        game.rng = SequenceRNG([5, 1, 4, 3, 4, 4, 3, 4, 3])
        order, bonus = game._initiative()
        self.assertEqual(set(order), {0, 1, 2})
        self.assertEqual(bonus, (True, False, False))
        with self.assertRaises(IllegalGroupAction):
            game._attack(0, GroupAction("hammer", (0,)))

    def test_stunned_target_grants_edge_and_mixed_fast_is_rejected(self):
        player = replace(blacklight_profile(),
                         powers=blacklight_profile().powers -
                         {"blazing_fast_fists"})
        game = GroupBattle(
            (player, lower_enemy("E1"), lower_enemy("E2")),
            (NoEdgeGroupPolicy("hammer", preferred="hammer"),
             GROUP_ENEMY, GROUP_ENEMY), seed=1, audit=True)
        game.round = 1
        game._reset_reactions()
        game.fighters[1].stunned_by = 0
        game.rng = SequenceRNG([3, 3, 3])
        game._attack(0, GroupAction("hammer", (1,)))
        check = next(e for e in game.log if e["type"] == "attack_check")
        self.assertEqual(check["edges"], 1)
        with self.assertRaises(NotImplementedError):
            game._attack(0, GroupAction("fast_strikes", (1, 2)))


if __name__ == "__main__":
    unittest.main()
