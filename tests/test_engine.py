"""Boundary and integration cases for the deliberately scoped duel engine."""

from dataclasses import replace
import unittest

from blacklight.damage import calculate
from blacklight.dice import DieRoll, classify, resolve_check
from blacklight.engine import (Action, Duel, IllegalAction, Move,
                               blacklight_profile, blade_second_strike_eligible)
from blacklight.policies import (ATTACK, BLADE_HAMMER_FAST, HAMMER, HEAL,
                                 KITER, SHIELD_HAMMER_ENDTURN,
                                 SHIELD_HAMMER_REACTIVE, STANCE)


class SequenceRNG:
    def __init__(self, sequence):
        self.sequence = iter(sequence)

    def randint(self, low, high):
        value = next(self.sequence)
        assert low <= value <= high
        return value


class TestEdgesAndDamage(unittest.TestCase):
    def test_edge_chooses_one_die_and_keeps_better(self):
        result, trace = resolve_check(SequenceRNG([1, 5, 2, 5]), 1, 10,
                                      edges=1, chooser=lambda *_: 0)
        self.assertEqual(result.roll, DieRoll(5, 5, 2))
        self.assertEqual(result.total, 13)
        self.assertEqual([(x.index, x.original, x.rolled, x.kept) for x in trace],
                         [(0, 1, 5, 5)])

    def test_edge_on_marvel_die_can_create_fantastic(self):
        result, _ = resolve_check(SequenceRNG([3, 5, 2, 1]), 0, 10,
                                  edges=1, chooser=lambda *_: 1)
        self.assertEqual(result.roll, DieRoll(3, 1, 2))
        self.assertTrue(result.fantastic)

    def test_trouble_replaces_marvel_logo_first(self):
        result, trace = resolve_check(SequenceRNG([6, 1, 5, 2]), 0, 10,
                                      troubles=1)
        self.assertEqual(result.roll, DieRoll(6, 2, 5))
        self.assertFalse(result.fantastic)
        self.assertEqual(trace[0].index, 1)

    def test_ultimate_ignores_trouble(self):
        result, trace = resolve_check(SequenceRNG([6, 1, 6]), 0, 30,
                                      troubles=2)
        self.assertTrue(result.success)
        self.assertTrue(result.ultimate)
        self.assertFalse(trace)

    def test_edge_and_trouble_cancel(self):
        result, trace = resolve_check(SequenceRNG([1, 5, 2]), 1, 10,
                                      edges=1, troubles=1)
        self.assertEqual(result.roll, DieRoll(1, 5, 2))
        self.assertFalse(trace)

    def test_dr_then_half_round_up(self):
        # FAQ 2025 p.4: DR is before a half-damage result; 29/2 becomes 15.
        self.assertEqual(calculate(4, 4, 5, [4], 2, False,
                                   denominator=2), 15)

    def test_blade_house_rule_gate_only(self):
        self.assertFalse(blade_second_strike_eligible(classify(DieRoll(5, 6, 5), 6, 16)))
        self.assertFalse(blade_second_strike_eligible(classify(DieRoll(1, 1, 1), 0, 30)))
        self.assertTrue(blade_second_strike_eligible(classify(DieRoll(6, 1, 6), 0, 30)))


class TestDuel(unittest.TestCase):
    @staticmethod
    def profiles():
        a = blacklight_profile()
        b = replace(a, name="Mirror")
        return a, b

    def test_fixed_seed_replays_full_log(self):
        def run():
            return Duel(self.profiles(), (ATTACK, ATTACK), seed=111,
                        audit=True).run()
        self.assertEqual(run(), run())

    def test_incapacitation_stops_duel(self):
        result = Duel(self.profiles(), (ATTACK, ATTACK), seed=7,
                      audit=True).run()
        self.assertEqual(result.outcome, "win")
        self.assertTrue(any(h <= 0 for h in result.final_health))
        self.assertFalse(any(x["type"] == "attack" and x["actor"] == result.winner
                             and x["health_before"] <= 0 for x in result.log))

    def test_horizon_is_inconclusive(self):
        wait = replace(ATTACK, always_wait=True)
        result = Duel(self.profiles(), (wait, wait), seed=5,
                      max_rounds=1).run()
        self.assertEqual(result.outcome, "inconclusive")
        self.assertIsNone(result.winner)

    def test_standard_and_movement_cannot_repeat(self):
        d = Duel(self.profiles(), (ATTACK, ATTACK), seed=1)
        d.active_actor = 0
        d.fighters[0].standard_available = True
        d.fighters[0].movement_available = True
        d._move(0, Move("stay", 0))
        with self.assertRaises(IllegalAction):
            d._move(0, Move("stay", 0))
        d._act(0, Action("wait"))
        with self.assertRaises(IllegalAction):
            d._act(0, Action("wait"))

    def test_out_of_range_attack_is_rejected(self):
        d = Duel(self.profiles(), (ATTACK, ATTACK), seed=1,
                 initial_distance=4)
        d.active_actor = 0
        d.fighters[0].standard_available = True
        with self.assertRaises(IllegalAction):
            d._act(0, Action("melee"))

    def test_focus_cost_cap_and_no_zero_focus(self):
        d = Duel(self.profiles(), (HEAL, ATTACK), seed=1)
        d.active_actor = 0
        d.fighters[0].standard_available = True
        d.fighters[0].health = 100
        self.assertNotIn(Action("heal", 16), d.legal_actions(0))
        d.fighters[0].focus = 5
        self.assertNotIn(Action("heal", 5), d.legal_actions(0))
        d.fighters[0].focus = 16
        d._act(0, Action("heal", 15))
        self.assertEqual((d.fighters[0].focus, d.fighters[0].health), (1, 130))

    def test_healing_factor_is_at_own_turn_end(self):
        d = Duel(self.profiles(), (ATTACK, ATTACK), seed=1, audit=True)
        d.fighters[0].health = 100
        d._turn(0)
        self.assertEqual(d.fighters[0].health, 105)
        self.assertEqual([x["type"] for x in d.log][-2:], ["heal", "turn_end"])

    def test_attack_stance_uses_standard_action_then_doubles_ability_bonus(self):
        a, b = self.profiles()
        b = replace(b, powers=b.powers - {"riposte"})
        d = Duel((a, b), (replace(STANCE, edge_mode="decline"), ATTACK),
                 seed=2, audit=True)
        d._turn(0)
        self.assertTrue(d.fighters[0].stance)
        self.assertFalse(any(x["type"] == "attack" for x in d.log))
        self.assertEqual(calculate(4, 3, 12, [3], 1, False), 32)
        d.rng = SequenceRNG([6, 4, 6])
        d._turn(0)
        self.assertEqual(d.fighters[1].health, 118)

    def test_reaction_budget_never_negative(self):
        for seed in range(50):
            result = Duel(self.profiles(), (ATTACK, ATTACK), seed=seed,
                          audit=True).run()
            for event in result.log:
                if event["type"] == "reaction_spent":
                    self.assertGreaterEqual(event["remaining"], 0)
                    self.assertLessEqual(event["remaining"], 1)

    def test_two_distinct_ripostes_then_third_is_rejected(self):
        a, b = self.profiles()
        a = replace(a, powers=a.powers - {"riposte", "blazing_fast_fists"})
        b = replace(b, powers=b.powers - {"blazing_fast_fists"})
        decline = replace(ATTACK, edge_mode="decline")
        d = Duel((a, b), (decline, replace(decline, always_wait=True)),
                 seed=1, audit=True)
        d.rng = SequenceRNG([1, 2, 1, 6, 6, 6,
                             1, 2, 1, 6, 6, 6,
                             1, 2, 1])
        for _ in range(3):
            d._attack(0, "melee")
            d._drain_events()
        self.assertEqual(d.fighters[1].ripostes, 2)
        self.assertEqual(d.fighters[1].reactions, 0)
        self.assertEqual(sum(x["type"] == "reaction_spent" for x in d.log), 2)

    def test_riposte_uses_policy_selected_hammer_and_stuns(self):
        a, b = self.profiles()
        a = replace(a, powers=a.powers - {"riposte", "blazing_fast_fists"})
        b = replace(b, powers=b.powers - {"blazing_fast_fists"})
        d = Duel((a, b), (replace(ATTACK, edge_mode="decline"),
                           replace(HAMMER, edge_mode="decline",
                                   knockback_stance=False)), seed=1, audit=True)
        d.rng = SequenceRNG([1, 2, 1, 6, 1, 6])
        d._attack(0, "melee")
        d._drain_events()
        reaction = [x for x in d.log if x["type"] == "attack" and x["reaction"]][0]
        self.assertEqual(reaction["mode"], "hammer")
        self.assertEqual(d.fighters[0].health, 54)
        self.assertEqual(d.fighters[0].stunned_by, 1)

    def test_blade_fantastic_riposte_does_not_grant_bonus_action(self):
        from blacklight.policies import BLADE

        a, b = self.profiles()
        a = replace(a, powers=a.powers - {"riposte", "blazing_fast_fists"})
        b = replace(b, powers=b.powers - {"blazing_fast_fists"})
        d = Duel((a, b), (replace(ATTACK, edge_mode="decline"),
                           replace(BLADE, edge_mode="decline")),
                 seed=1, audit=True)
        d.rng = SequenceRNG([1, 2, 1, 6, 1, 6])
        d._attack(0, "melee")
        d._drain_events()
        reactions = [e for e in d.log if e["type"] == "attack" and e["reaction"]]
        self.assertEqual(len(reactions), 1)
        self.assertEqual(reactions[0]["mode"], "blade")
        self.assertTrue(reactions[0]["fantastic"])
        self.assertEqual(d.fighters[1].blade_bonus_actions, 0)
        self.assertFalse(any(e["type"] == "blade_bonus" for e in d.log))

    def test_double_movement_reaches_target(self):
        d = Duel(self.profiles(), (ATTACK, ATTACK), seed=1,
                 initial_distance=9, audit=True)
        d._turn(0)
        self.assertEqual(d.distance, 1)
        movements = [x for x in d.log if x["type"] == "movement"]
        self.assertEqual([x["as_standard"] for x in movements], [False, True])
        self.assertEqual([x["steps"] for x in movements], [5, 3])

    def test_ranged_kiter_can_attack_then_move(self):
        from blacklight.experiment import scenarios
        gunner = next(x for x in scenarios() if x.id == "gunner_kiter").opponent
        _, b = self.profiles()
        d = Duel((gunner, b), (KITER, ATTACK), seed=1, audit=True)
        d._turn(0)
        self.assertEqual(d.distance, 7)
        events = [x["type"] for x in d.log]
        self.assertLess(events.index("attack"), events.index("movement"))

    def test_kiter_uses_second_retreat_against_equally_fast_pursuer(self):
        from blacklight.experiment import scenarios
        scenario = next(x for x in scenarios() if x.id == "gunner_kiter")
        faster_victor = replace(blacklight_profile(), run_speed=6,
                                run_speed_exception=True)
        d = Duel((scenario.opponent, faster_victor),
                 (scenario.policy, ATTACK), seed=1, audit=True)
        d._turn(0)
        self.assertEqual(d.distance, 13)
        movements = [x for x in d.log if x["type"] == "movement"]
        self.assertEqual([x["as_standard"] for x in movements], [True, False])
        self.assertFalse(any(x["type"] == "attack" for x in d.log))

    def test_initiative_fantastic_creates_bonus_round_eligibility(self):
        d = Duel(self.profiles(), (replace(ATTACK, edge_mode="decline"),
                                   replace(ATTACK, edge_mode="decline")), seed=1)
        d.rng = SequenceRNG([6, 1, 6, 6, 6, 6])
        order, bonus = d._initiative()
        self.assertEqual(order, (0, 1))
        self.assertEqual(bonus, (True, False))

    def test_sheet_literal_initiative_and_run_are_separate_variant(self):
        a, b = self.profiles()
        sheet = replace(a, initiative_modifier=1, run_speed=6,
                        run_speed_exception=True)
        decline = replace(ATTACK, edge_mode="decline")
        d = Duel((sheet, b), (decline, decline), seed=1, audit=True)
        d.rng = SequenceRNG([6, 6, 6, 6, 6, 6])
        order, _ = d._initiative()
        self.assertEqual(order, (1, 0))
        d.active_actor = 0
        d.fighters[0].movement_available = True
        d.distance = 7
        d._move(0, Move("approach", 6))
        self.assertEqual(d.distance, 1)

    def test_policy_owns_edge_choice(self):
        a, b = self.profiles()
        d1 = Duel((a, b), (replace(ATTACK, edge_mode="decline"), ATTACK), seed=1,
                  audit=True)
        d1.rng = SequenceRNG([3, 5, 2])
        d1._attack(0, "melee")
        d2 = Duel((a, b), (replace(ATTACK, edge_mode="marvel"), ATTACK), seed=1,
                  audit=True)
        d2.rng = SequenceRNG([3, 5, 2, 1])
        d2._attack(0, "melee")
        self.assertFalse([x for x in d1.log if x["type"] == "attack"][0]["fantastic"])
        self.assertTrue([x for x in d2.log if x["type"] == "attack"][0]["fantastic"])

    def test_shield_stacks_with_sturdy_only_by_house_rule(self):
        a, b = self.profiles()
        no_shield = Duel((a, b), (replace(ATTACK, edge_mode="decline"), ATTACK), seed=1)
        no_shield.rng = SequenceRNG([6, 4, 6])
        no_shield._attack(0, "melee")
        shield = Duel((a, replace(b, shield_active=True)),
                      (replace(ATTACK, edge_mode="decline"), ATTACK), seed=1)
        shield.rng = SequenceRNG([6, 4, 6])
        shield._attack(0, "melee")
        self.assertEqual((no_shield.fighters[1].health,
                          shield.fighters[1].health), (124, 132))

    def test_shield_reaction_after_hit_protects_same_attack(self):
        a, b = self.profiles()
        attacker = replace(HAMMER, edge_mode="decline")
        defender = replace(SHIELD_HAMMER_REACTIVE, edge_mode="decline",
                           riposte=False)
        d = Duel((a, b), (attacker, defender), seed=1, audit=True)
        d.rng = SequenceRNG([6, 4, 6])
        d._attack(0, "hammer")
        self.assertEqual(d.fighters[1].health, 124)
        self.assertTrue(d.fighters[1].shield_active)
        self.assertEqual(d.fighters[1].reactions, 1)
        attack = next(x for x in d.log if x["type"] == "attack")
        self.assertEqual((attack["reduction"], attack["damage"]), (3, 26))
        self.assertLess(next(x["seq"] for x in d.log if x["type"] == "shield_activate"),
                        attack["seq"])

    def test_shield_reaction_waits_for_a_hit(self):
        a, b = self.profiles()
        d = Duel((a, b), (replace(ATTACK, edge_mode="decline"),
                           replace(SHIELD_HAMMER_REACTIVE, riposte=False)),
                 seed=1, audit=True)
        d.rng = SequenceRNG([1, 2, 1])
        d._attack(0, "melee")
        self.assertFalse(d.fighters[1].shield_active)
        self.assertEqual(d.fighters[1].reactions, 2)

    def test_shield_reaction_blocks_the_triggering_ammunition_hit(self):
        from blacklight.experiment import scenarios

        gunner = next(s.opponent for s in scenarios()
                      if s.id == "gunner_kiter")
        victor = blacklight_profile()
        d = Duel((gunner, victor), (ATTACK, SHIELD_HAMMER_REACTIVE),
                 seed=1, initial_distance=8, audit=True)
        d.rng = SequenceRNG([6, 4, 6])
        d._attack(0, "ranged")
        attack = next(x for x in d.log if x["type"] == "attack")
        self.assertTrue(attack["success"])
        self.assertTrue(attack["ammunition_immunity"])
        self.assertEqual(attack["damage"], 0)
        self.assertTrue(d.fighters[1].shield_active)

    def test_shield_standard_action_persists_until_free_deactivation(self):
        from blacklight.policies import RulePolicy

        a, b = self.profiles()
        policy = RulePolicy("shield_standard_test", weapon="hammer",
                            shield_standard=True, edge_mode="decline")
        d = Duel((a, b), (policy, ATTACK), seed=1, audit=True)
        d._turn(0)
        self.assertTrue(d.fighters[0].shield_active)
        self.assertFalse(any(x["type"] == "attack" for x in d.log))
        self.assertEqual(d.fighters[0].reactions, 2)
        d.rng = SequenceRNG([6, 4, 6])
        d._turn(0)
        self.assertFalse(d.fighters[0].shield_active)
        self.assertTrue(any(x["type"] == "attack" for x in d.log))

    def test_shield_end_turn_reaction_after_standard_attack(self):
        a, b = self.profiles()
        d = Duel((a, b), (replace(SHIELD_HAMMER_ENDTURN,
                                  edge_mode="decline"), ATTACK),
                 seed=1, audit=True)
        d.rng = SequenceRNG([6, 4, 6])
        d._turn(0)
        events = [x["type"] for x in d.log]
        self.assertLess(events.index("attack"), events.index("shield_activate"))
        self.assertTrue(d.fighters[0].shield_active)
        self.assertEqual(d.fighters[0].reactions, 1)
        d.rng = SequenceRNG([6, 4, 6])
        d._attack(0, "hammer")
        self.assertFalse(d.fighters[0].shield_active)
        self.assertTrue(any(x["type"] == "shield_deactivate" for x in d.log))

    def test_reactions_do_not_refresh_when_own_turn_starts_mid_round(self):
        a, b = self.profiles()
        d = Duel((a, b), (replace(HAMMER, edge_mode="decline"),
                           replace(SHIELD_HAMMER_REACTIVE,
                                   edge_mode="decline")),
                 seed=1, audit=True)
        d.round = 1
        d._reset_reactions_for_round()
        d.rng = SequenceRNG([6, 4, 6, 6, 4, 6])
        d._attack(0, "hammer")
        self.assertEqual(d.fighters[1].reactions, 1)
        d._turn(1)
        self.assertEqual(d.fighters[1].reactions, 1)
        turn_start = next(x for x in d.log if x["type"] == "turn_start")
        self.assertEqual(turn_start["reactions"], 1)

    def test_shield_is_not_a_fast_strikes_offhand(self):
        a, b = self.profiles()
        d = Duel((a, b), (ATTACK, ATTACK), seed=1)
        d.active_actor = 0
        d.fighters[0].standard_available = True
        self.assertNotIn(Action("hammer_fast", offhand="shield"),
                         d.legal_actions(0))
        with self.assertRaises(IllegalAction):
            d._attack(0, "hammer_fast", offhand="shield")

    def test_hammer_fantastic_stuns_and_breaks_stance(self):
        a, b = self.profiles()
        b = replace(b, powers=b.powers - {"riposte"})
        policy = replace(ATTACK, edge_mode="decline", weapon="hammer",
                         knockback_stance=False)
        d = Duel((a, b), (policy, ATTACK), seed=1, audit=True)
        d.fighters[1].stance = True
        d.rng = SequenceRNG([6, 1, 6])
        d._attack(0, "hammer")
        self.assertFalse(d.fighters[1].stance)
        self.assertEqual(d.fighters[1].stunned_by, 0)
        self.assertEqual(d.fighters[1].health, 54)
        d._turn(1)
        self.assertIn("turn_skipped", [x["type"] for x in d.log])
        d.rng = SequenceRNG([2, 2, 2, 6])
        d._turn(0)
        self.assertIsNone(d.fighters[1].stunned_by)

    def test_blade_hammer_fast_grants_one_extra_roll_only(self):
        a, b = self.profiles()
        b = replace(b, powers=b.powers - {"riposte"})
        p = replace(BLADE_HAMMER_FAST, edge_mode="decline")
        d = Duel((a, b), (p, ATTACK), seed=1, audit=True)
        d.active_actor = 0
        d.fighters[0].standard_available = True
        d.rng = SequenceRNG([6, 1, 6, 6, 1, 6])
        d._act(0, Action("blade_fast", offhand="hammer"))
        self.assertEqual(sum(x["type"] == "blade_bonus" for x in d.log), 1)
        self.assertEqual(sum(x["type"] == "attack" for x in d.log), 2)
        self.assertEqual(d.fighters[1].limb_stage, 2)
        self.assertEqual(d.fighters[1].health, 54)
        self.assertEqual(d.fighters[1].bleeding, 5)

    def test_blade_regular_hit_does_not_grant_second_action(self):
        a, b = self.profiles()
        b = replace(b, powers=b.powers - {"riposte"})
        p = replace(BLADE_HAMMER_FAST, edge_mode="decline")
        d = Duel((a, b), (p, ATTACK), seed=1, audit=True)
        d.active_actor = 0
        d.fighters[0].standard_available = True
        d.rng = SequenceRNG([6, 6, 6])
        d._act(0, Action("blade_fast", offhand="hammer"))
        self.assertEqual(sum(x["type"] == "attack" for x in d.log), 1)
        self.assertEqual(sum(x["type"] == "blade_bonus" for x in d.log), 0)

    def test_mighty_knockback_breaks_stance(self):
        a, b = self.profiles()
        d = Duel((a, b), (replace(ATTACK, edge_mode="decline"), ATTACK),
                 seed=1, audit=True)
        d.fighters[1].stance = True
        d.rng = SequenceRNG([6, 1, 6])
        d._attack(0, "melee")
        self.assertFalse(d.fighters[1].stance)
        self.assertEqual(d.distance, 26)  # 5 × (Rank 3 + Mighty 3 − DR 1)

    def test_hammer_fantastic_chooses_knockback_instead_of_stunned(self):
        a, b = self.profiles()
        d = Duel((a, b), (replace(HAMMER, edge_mode="decline"), ATTACK),
                 seed=1, audit=True)
        d.fighters[1].stance = True
        d.rng = SequenceRNG([6, 1, 6])
        d._attack(0, "hammer")
        self.assertIsNone(d.fighters[1].stunned_by)
        self.assertFalse(d.fighters[1].stance)
        self.assertEqual(d.distance, 36)  # Rank 3 + Mighty 3 + Marreta 2 - DR 1

    def test_dodge_consumes_action_and_causes_trouble_until_next_turn(self):
        a, b = self.profiles()
        a = replace(a, powers=a.powers - {"blazing_fast_fists"})
        decline = replace(ATTACK, edge_mode="decline")
        d = Duel((a, b), (decline, replace(decline, always_wait=True)),
                 seed=1, audit=True)
        d.active_actor = 1
        d.fighters[1].standard_available = True
        d._act(1, Action("dodge"))
        d.active_actor = None
        self.assertTrue(d.fighters[1].dodging)
        d.rng = SequenceRNG([6, 6, 6, 1])
        d._attack(0, "melee")
        attack = [x for x in d.log if x["type"] == "attack"][0]
        self.assertEqual(attack["rerolls"][0]["kind"], "trouble")
        d.rng = SequenceRNG([6, 6, 6])
        d._turn(1)
        self.assertFalse(d.fighters[1].dodging)

    def test_bleeding_ticks_on_victims_turn_and_dr_reduces_it(self):
        a, b = self.profiles()
        b = replace(b, health_dr=0, powers=b.powers - {"healing_factor", "riposte"})
        d = Duel((a, b), (replace(ATTACK, edge_mode="decline"),
                           replace(ATTACK, always_wait=True)), seed=1, audit=True)
        d.rng = SequenceRNG([6, 6, 6])
        d._attack(0, "blade")
        before = d.fighters[1].health
        d._turn(1)
        self.assertEqual(d.fighters[1].health, before - 5)
        self.assertEqual(d.fighters[1].bleeding, 5)

    def test_gunner_treats_bleeding_while_retreating(self):
        from blacklight.experiment import scenarios
        scenario = next(x for x in scenarios() if x.id == "gunner_kiter")
        d = Duel((blacklight_profile(), scenario.opponent),
                 (ATTACK, scenario.policy), seed=1, initial_distance=3,
                 audit=True)
        d.fighters[1].bleeding = 5
        d.rng = SequenceRNG([6, 6, 6])
        d._turn(1)
        self.assertEqual(d.fighters[1].bleeding, 0)
        self.assertEqual(d.distance, 9)
        kinds = [x["type"] for x in d.log]
        self.assertIn("condition_treatment", kinds)
        self.assertNotIn("attack", kinds)
        self.assertNotIn("condition_tick", kinds)

    def test_healing_factor_ends_bleeding(self):
        d = Duel(self.profiles(), (replace(ATTACK, always_wait=True), ATTACK),
                 seed=1, audit=True)
        d.fighters[0].health = 100
        d.fighters[0].bleeding = 5
        d._turn(0)
        self.assertEqual(d.fighters[0].health, 105)
        self.assertEqual(d.fighters[0].bleeding, 0)

    def test_end_turn_healing_bleeding_order_is_explicit_variant(self):
        a, b = self.profiles()
        a = replace(a, health_dr=0)
        wait = replace(ATTACK, always_wait=True)
        before = Duel((a, b), (wait, ATTACK), seed=1,
                      end_turn_healing_first=True)
        after = Duel((a, b), (wait, ATTACK), seed=1,
                     end_turn_healing_first=False)
        for duel in (before, after):
            duel.fighters[0].health = 100
            duel.fighters[0].bleeding = 5
            duel._turn(0)
        self.assertEqual(before.fighters[0].health, 105)
        self.assertEqual(after.fighters[0].health, 100)
        self.assertEqual((before.fighters[0].bleeding,
                          after.fighters[0].bleeding), (0, 0))

    def test_shield_immunity_to_ammunition_in_rank_three(self):
        a, b = self.profiles()
        gunner = replace(a, name="Gunner", ranged_range=10,
                         ranged_is_ammunition=True, weapons=frozenset(),
                         powers=frozenset())
        shielded = replace(b, shield_active=True)
        d = Duel((gunner, shielded), (ATTACK, ATTACK), seed=1,
                 initial_distance=3, audit=True)
        d.rng = SequenceRNG([6, 6, 6])
        d._attack(0, "ranged")
        self.assertEqual(d.fighters[1].health, 150)
        self.assertEqual([x for x in d.log if x["type"] == "attack"][0]["damage"], 0)

    def test_heroic_attack_stops_short_of_killing(self):
        a, b = self.profiles()
        b = replace(b, max_health=10, health_dr=0)
        d = Duel((a, b), (replace(ATTACK, edge_mode="decline"), ATTACK),
                 seed=1, audit=True)
        d.rng = SequenceRNG([6, 1, 6])
        d._attack(0, "melee")
        self.assertEqual(d.fighters[1].health, -9)


if __name__ == "__main__":
    unittest.main()
