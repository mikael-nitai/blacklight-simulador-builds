"""Direct oracles for the latest master ruling, independent of damage helpers."""

from copy import deepcopy
from dataclasses import replace
import unittest

from blacklight.audit import audit_log
from blacklight.engine import Action, IllegalAction, Profile, blacklight_profile
from blacklight.policies import ATTACK
from combatants.split_fast import FastAction, SplitFastDuel, SplitFastPolicy


COMMON, FANTASTIC, MISS = (6, 6, 6), (2, 1, 2), (2, 2, 2)


class Dice:
    def __init__(self, values, timeline, label):
        self.values, self.timeline, self.label = iter(values), timeline, label

    def randint(self, low, high):
        value = next(self.values)
        assert low <= value <= high
        self.timeline.append(self.label)
        return value


def game(*, effect=0, rolls=COMMON + COMMON, foe=None, policy=None, stack_stunned=False):
    hero = replace(blacklight_profile(), heroic=False)
    opponent = foe or Profile('Target', 3, 1000, 90, 4, 2, 3, 2, 14, 12, 5)
    policy = policy or SplitFastPolicy('control', weapon='hammer', offhand='blade',
                                        prefer_fast=True, effect_limb=effect,
                                        edge_mode='decline', riposte=False)
    battle = SplitFastDuel((hero, opponent), (policy, ATTACK), seed=1, audit=True,
                            stack_stunned_edge=stack_stunned)
    battle.round = 1
    battle._reset_reactions_for_round()
    battle.active_actor = 0
    battle.fighters[0].standard_available = True
    timeline = []
    battle.rng = Dice(rolls, timeline, 'hit')
    battle.damage_rng = Dice([1] * 100, timeline, 'damage')
    return battle, timeline


def audit(battle):
    return audit_log(battle.log, {f.profile.name: f.profile.max_health for f in battle.fighters},
                     {f.profile.name: f.profile.max_focus for f in battle.fighters})


class TestSplitFast(unittest.TestCase):
    def test_both_checks_before_damage_and_pre_effect_edges_are_frozen(self):
        battle, timeline = game(rolls=FANTASTIC + MISS, stack_stunned=True)
        battle._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=0))
        attacks = [row for row in battle.log if row['type'] == 'attack']
        self.assertEqual(timeline[:6], ['hit'] * 6)
        self.assertEqual([row['edges'] for row in attacks], [2, 2])
        checks = [row['seq'] for row in battle.log if row['type'] == 'fast_limb_check']
        first_effect = min(row['seq'] for row in battle.log if row['type'] == 'condition_start')
        self.assertLess(max(checks), first_effect)
        self.assertEqual(audit(battle), [])

    def test_hand_calculated_per_limb_damage_matrix(self):
        cases = ((COMMON, COMMON, 48), (FANTASTIC, COMMON, 75),
                 (COMMON, FANTASTIC, 75), (FANTASTIC, FANTASTIC, 102),
                 (MISS, COMMON, 21), (COMMON, MISS, 27), (MISS, MISS, 0))
        for first, second, expected in cases:
            battle, _ = game(rolls=first + second)
            battle._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=0))
            self.assertEqual(1000 - battle.fighters[1].health, expected)
            self.assertEqual(battle.fighters[0].attacks, 2)
            self.assertEqual(audit(battle), [])

    def test_selecting_hammer_disables_all_blade_effects_even_on_fantastic(self):
        battle, _ = game(rolls=COMMON + FANTASTIC)
        battle._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=0))
        target = battle.fighters[1]
        self.assertEqual((target.bleeding, target.limb_stage, target.stunned_by), (0, 0, None))
        self.assertEqual(battle.fighters[0].blade_bonus_actions, 0)
        self.assertEqual(audit(battle), [])

    def test_selecting_blade_disables_hammer_stun_and_preserves_ordinary_bleeding(self):
        battle, _ = game(effect=1, rolls=FANTASTIC + COMMON)
        battle._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=1))
        target = battle.fighters[1]
        self.assertEqual((target.bleeding, target.limb_stage, target.stunned_by), (5, 0, None))
        self.assertEqual(battle.fighters[0].blade_bonus_actions, 0)
        self.assertEqual(audit(battle), [])

    def test_only_selected_blade_fantastic_grants_one_new_action_with_new_checks(self):
        policy = SplitFastPolicy('blade_control', weapon='blade', offhand='hammer',
                                  prefer_fast=True, effect_limb=0, edge_mode='decline', riposte=False)
        battle, timeline = game(policy=policy, rolls=FANTASTIC * 4)
        battle._act(0, FastAction('blade_fast', offhand='hammer', effect_limb=0))
        self.assertEqual(battle.fighters[0].attacks, 4)
        self.assertEqual(battle.fighters[0].blade_bonus_actions, 1)
        self.assertEqual(sum(row['type'] == 'fast_use_start' for row in battle.log), 2)
        self.assertEqual(timeline.count('hit'), 12)
        self.assertEqual(battle.fighters[1].health, 1000 - 204)
        self.assertIsNone(battle.fighters[1].stunned_by)
        self.assertEqual(audit(battle), [])

    def test_same_weapon_pair_still_selects_only_one_effect_limb(self):
        battle, _ = game(rolls=FANTASTIC + COMMON)
        battle._act(0, FastAction('blade_fast', effect_limb=1))
        self.assertEqual(battle.fighters[1].bleeding, 5)
        self.assertEqual(battle.fighters[1].limb_stage, 0)
        self.assertEqual(battle.fighters[0].blade_bonus_actions, 0)
        self.assertEqual(audit(battle), [])

    def test_both_effects_before_riposte_can_cancel_counter_to_other_miss(self):
        foe = Profile('Target', 3, 1000, 90, 4, 2, 3, 2, 14, 12, 5,
                       powers=frozenset({'riposte'}))
        battle, timeline = game(effect=1, rolls=MISS + FANTASTIC, foe=foe)
        battle._act(0, FastAction('blade_fast', offhand='hammer', effect_limb=1))
        self.assertEqual(battle.fighters[1].stunned_by, 0)
        self.assertEqual(battle.fighters[1].ripostes, 0)
        self.assertEqual(timeline.count('hit'), 6)
        self.assertFalse(any(row['type'] == 'reaction_spent' for row in battle.log))
        self.assertEqual(audit(battle), [])

    def test_shield_after_both_checks_before_damage_reduces_each_component(self):
        foe = Profile('Target', 3, 1000, 90, 4, 2, 3, 2, 14, 12, 5, health_dr=1,
                       weapons=frozenset({'shield'}))
        battle, _ = game(foe=foe)
        battle.policies = (battle.policies[0], replace(ATTACK, shield_react=True))
        battle._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=0))
        self.assertEqual(1000 - battle.fighters[1].health, 30)
        checks = [row['seq'] for row in battle.log if row['type'] == 'fast_limb_check']
        shield = next(row['seq'] for row in battle.log if row['type'] == 'shield_activate')
        attacks = [row['seq'] for row in battle.log if row['type'] == 'attack']
        self.assertLess(max(checks), shield)
        self.assertLess(shield, min(attacks))
        self.assertEqual(audit(battle), [])

    def test_unselected_effect_and_changed_choice_tampering_are_detected(self):
        battle, _ = game(rolls=COMMON + FANTASTIC)
        battle._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=0))
        changed = deepcopy(battle.log)
        row = next(row for row in changed if row['type'] == 'attack' and row['limb'] == 1)
        row['effect_limb'], row['effects_enabled'] = 1, True
        self.assertTrue(any('predeclared' in issue for issue in audit_log(
            changed, {'Blacklight': 150, 'Target': 1000}, {'Blacklight': 90, 'Target': 90})))

    def test_effect_choice_is_required_before_standard_or_rng_is_spent(self):
        battle, timeline = game()
        before = len(battle.log)
        with self.assertRaises(IllegalAction):
            battle._act(0, Action('hammer_fast', offhand='blade'))
        self.assertTrue(battle.fighters[0].standard_available)
        self.assertEqual((len(battle.log), timeline), (before, []))
        for choice in (None, False, 0.0, -1, 2):
            with self.assertRaises(ValueError):
                FastAction('blade_fast', effect_limb=choice)

    def test_two_checks_still_spend_only_one_standard_action(self):
        battle, _ = game()
        action = FastAction('hammer_fast', offhand='blade', effect_limb=0)
        battle._act(0, action)
        before = len(battle.log)
        with self.assertRaises(IllegalAction):
            battle._act(0, action)
        self.assertEqual(len(battle.log), before)
        self.assertEqual(audit(battle), [])

    def test_false_bonus_action_label_is_rejected_by_independent_ledger(self):
        battle, _ = game()
        battle._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=0))
        changed = deepcopy(battle.log)
        next(row for row in changed if row['type'] == 'fast_use_start')['bonus_action'] = True
        issues = audit_log(changed, {'Blacklight': 150, 'Target': 1000},
                            {'Blacklight': 90, 'Target': 90})
        self.assertTrue(any('bonus declaration mismatch' in issue for issue in issues))

    def test_standard_blade_fantastic_can_grant_one_new_fast_use(self):
        policy = SplitFastPolicy('blade', weapon='blade', offhand='hammer', prefer_fast=True,
                                  effect_limb=0, edge_mode='decline', riposte=False)
        battle, _ = game(policy=policy, rolls=FANTASTIC * 3)
        battle._act(0, Action('blade'))
        self.assertEqual((battle.fighters[0].attacks, battle.fighters[0].blade_bonus_actions), (3, 1))
        self.assertEqual(1000 - battle.fighters[1].health, 198)
        self.assertEqual(audit(battle), [])

    def test_fantastic_blade_riposte_after_joint_checks_does_not_grant_extra_action(self):
        foe = Profile('Target', 3, 1000, 90, 4, 2, 3, 2, 14, 12, 5,
                       powers=frozenset({'riposte'}), weapons=frozenset({'blade'}))
        battle, timeline = game(foe=foe, rolls=MISS + MISS + (6, 1, 6))
        battle.policies = (battle.policies[0], replace(ATTACK, weapon='blade', edge_mode='decline'))
        battle._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=0))
        self.assertEqual(battle.fighters[1].ripostes, 1)
        self.assertEqual(battle.fighters[1].blade_bonus_actions, 0)
        self.assertFalse(any(row['type'] == 'blade_bonus' for row in battle.log))
        self.assertEqual(timeline.count('hit'), 9)
        self.assertEqual(audit(battle), [])


if __name__ == '__main__':
    unittest.main()
