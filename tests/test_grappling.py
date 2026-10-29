from dataclasses import replace
from itertools import product
import unittest

from blacklight.dice import DieRoll, RerollTrace
from experimental.grappling import (GrapplingState, escape, grappling_technique, movement_allowed,
                                    pinned_check_trouble, release)
from experimental.grappling_audit import audit_escape, audit_grappling
from experimental.reaction_pools import ReactionPools


def state(**changes):
    base = GrapplingState(attacker_rank=3, attacker_focus=10, attacker_standard=True,
                          attacker_conscious=True, attacker_stunned=False,
                          target_health=100, target_standard=True, target_stunned=False,
                          target_reactions=ReactionPools(2, 0), distance=1)
    return replace(base, **changes)


class GrapplingTransactionsTests(unittest.TestCase):
    def test_hit_miss_and_fantastic_with_zero_damage(self):
        for hit, fantastic, damage, grabbed, pinned in ((False, False, 0, False, False),
                (True, False, 0, True, False), (True, True, 0, True, True),
                (True, True, 20, True, True)):
            with self.subTest(hit=hit, fantastic=fantastic, damage=damage):
                result = grappling_technique(state(), has_power=True, attack_success=hit,
                    fantastic_success=fantastic, applied_damage=damage, trigger=1)
                self.assertEqual((result.after.grabbed, result.after.pinned), (grabbed, pinned))
                self.assertEqual((result.after.attacker_focus, result.after.attacker_standard,
                                  result.after.target_health), (5, False, 100 - damage))
                self.assertEqual(result.before, state())

    def test_unavailable_attacks_and_invalid_claims_fail_without_mutation(self):
        for invalid in (state(attacker_rank=1), state(attacker_focus=5),
                        state(attacker_standard=False), state(attacker_stunned=True),
                        state(attacker_conscious=False), state(distance=2),
                        state(target_health=0), state(grabbed=True)):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                grappling_technique(invalid, has_power=True, attack_success=True,
                                     fantastic_success=False, applied_damage=3, trigger=1)
        for hit, fantastic, damage in ((False, True, 0), (False, False, 1)):
            with self.assertRaises(ValueError):
                grappling_technique(state(), has_power=True, attack_success=hit,
                                     fantastic_success=fantastic, applied_damage=damage, trigger=1)

    def test_mighty_applies_to_escape_not_attack_and_action_is_consumed(self):
        held = state(grabbed=True)
        args = dict(timing='standard', melee=6, grabber_melee_defense=14,
                    roll=DieRoll(2, 2, 2), rerolls=())
        failed = escape(held, mighty=0, **args)
        success = escape(held, mighty=3, **args)
        self.assertEqual((failed.total, failed.success, failed.after.grabbed), (12, False, True))
        self.assertEqual((success.total, success.success, success.after.grabbed), (15, True, False))
        self.assertFalse(failed.after.target_standard)
        self.assertFalse(success.after.target_standard)

    def test_pinned_escape_requires_valid_trouble_and_removes_both_conditions(self):
        held = state(grabbed=True, pinned=True)
        trace = (RerollTrace('trouble', 1, 4, 1, 4),)
        result = escape(held, timing='standard', melee=6, mighty=3, grabber_melee_defense=14,
                        roll=DieRoll(3, 4, 2), rerolls=trace)
        self.assertEqual((result.total, result.troubles, result.success), (18, 1, True))
        self.assertFalse(result.after.grabbed or result.after.pinned)
        with self.assertRaisesRegex(ValueError, 'trouble'):
            escape(held, timing='standard', melee=6, mighty=3, grabber_melee_defense=14,
                   roll=DieRoll(3, 4, 2), rerolls=())
        ultimate = escape(held, timing='standard', melee=0, mighty=0, grabber_melee_defense=40,
                          roll=DieRoll(6, 1, 6), rerolls=())
        self.assertTrue(ultimate.success)

    def test_reaction_pool_is_restricted_and_same_trigger_cannot_be_reused(self):
        held = state(grabbed=True, target_reactions=ReactionPools(1, 1, frozenset({7})))
        args = dict(timing='reaction', melee=6, mighty=3, grabber_melee_defense=14,
                    roll=DieRoll(2, 2, 2), rerolls=())
        with self.assertRaises(ValueError):
            escape(held, trigger=7, **args)
        result = escape(held, trigger=8, **args)
        self.assertEqual(result.after.target_reactions, ReactionPools(0, 1, frozenset({7, 8})))
        self.assertTrue(result.after.target_standard)
        with self.assertRaises(ValueError):
            escape(replace(held, target_reactions=ReactionPools(0, 1)), trigger=8, **args)

    def test_hold_limits_movement_and_pinned_checks_until_release(self):
        held = state(grabbed=True, pinned=True)
        for actor in ('attacker', 'target'):
            self.assertFalse(movement_allowed(held, actor))
            with self.assertRaises(ValueError):
                movement_allowed(held, actor, carrying=True)
        for ability in ('melee', 'agility', 'logic'):
            self.assertEqual(pinned_check_trouble(held, 'target', ability), int(ability != 'logic'))
            self.assertEqual(pinned_check_trouble(held, 'attacker', ability), 0)
        freed = release(held, 'attacker')
        self.assertTrue(movement_allowed(freed, 'target'))
        self.assertFalse(freed.grabbed or freed.pinned)
        with self.assertRaises(ValueError):
            release(held, 'target')

    def test_ordinary_escape_all_216_faces_against_independent_arithmetic(self):
        held = state(grabbed=True)
        successes = 0
        for left, marvel, right in product(range(1, 7), repeat=3):
            result = escape(held, timing='standard', melee=6, mighty=3, grabber_melee_defense=14,
                            roll=DieRoll(left, marvel, right), rerolls=())
            expected_total = left + (6 if marvel == 1 else marvel) + right + 9
            expected_success = (left, marvel, right) == (6, 1, 6) or expected_total >= 14
            self.assertEqual((result.total, result.success), (expected_total, expected_success))
            successes += int(result.success)
        self.assertEqual(successes, 215)

    def test_pinned_escape_exhaustive_dice_and_trouble(self):
        held = state(grabbed=True, pinned=True)
        successes = 0
        for left, marvel, right, fresh in product(range(1, 7), repeat=4):
            initial = (left, marvel, right)
            if initial == (6, 1, 6):
                final, trace = initial, ()
            else:
                quality = [(6, 1) if i == 1 and value == 1 else (value, 0)
                           for i, value in enumerate(initial)]
                chosen = max(range(3), key=lambda i: (quality[i], -i))
                new_quality = (6, 1) if chosen == 1 and fresh == 1 else (fresh, 0)
                kept = fresh if new_quality < quality[chosen] else initial[chosen]
                values = list(initial)
                values[chosen] = kept
                final = tuple(values)
                trace = (RerollTrace('trouble', chosen, initial[chosen], fresh, kept),)
            result = escape(held, timing='standard', melee=6, mighty=3,
                            grabber_melee_defense=14, roll=DieRoll(*final), rerolls=trace)
            successes += int(result.success)
        # Only 20 of the 1,296 equally likely initial-roll/fresh-face pairs
        # end at 1,2,1, the sole failure when the modifier is +9 and TN is 14.
        self.assertEqual(successes, 1276)

    def test_independent_auditor_detects_falsified_transitions(self):
        facts = dict(has_power=True, attack_success=True, fantastic_success=True,
                     applied_damage=0, trigger=7)
        result = grappling_technique(state(), **facts)
        self.assertEqual(audit_grappling(result, **facts), [])
        self.assertTrue(audit_grappling(replace(result, after=replace(result.after, pinned=False)), **facts))
        self.assertTrue(audit_grappling(replace(result, attack_success=1), **facts))
        self.assertTrue(audit_grappling(result, **dict(facts, applied_damage=1)))
        trace = (RerollTrace('trouble', 1, 4, 1, 4),)
        escaped = escape(result.after, timing='reaction', melee=6, mighty=3,
                         grabber_melee_defense=14, roll=DieRoll(3, 4, 2), rerolls=trace, trigger=8)
        expected = dict(timing='reaction', melee=6, mighty=3, grabber_melee_defense=14, trigger=8)
        self.assertEqual(audit_escape(escaped, **expected), [])
        self.assertTrue(audit_escape(replace(escaped, total=escaped.total + 1), **expected))
        self.assertTrue(audit_escape(replace(escaped, after=replace(escaped.after, target_reactions=
                         result.after.target_reactions)), **expected))
