from copy import deepcopy
from dataclasses import replace
import unittest

from blacklight.engine import IllegalAction, Profile
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.sheets import load_sheet
from experimental.mental_punch_split_audit import audit_mental_punch_split
from experimental.mental_punch_split_duel import MentalPunchPolicy, MentalPunchSplitDuel
from scripts.crossbones_ram_demo import VICTOR


class MentalPunchSplitDuelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.victor = compile_duel(load_sheet(VICTOR))
        cls.foe = Profile('Mentalista sintético', 4, 500, 90, 6, 0, 5, 2, 16, 10, 5,
                          initiative_modifier=100, powers=frozenset({'mental_punch'}))

    def run_case(self, seed, *, focus=90, shield=False, heroic_foe=False, wait=False):
        hero = replace(self.victor, max_focus=focus)
        foe = replace(self.foe, heroic=heroic_foe)
        profiles = (hero, foe)
        policies = (MentalPunchPolicy('victor', weapon='hammer', offhand='blade', prefer_fast=True,
                        shield_react=shield, shield_against_mental=shield, always_wait=wait),
                    MentalPunchPolicy('mentalista', prefer_mental_punch=True))
        duel = MentalPunchSplitDuel(profiles, policies, seed=seed, initial_distance=1,
            max_rounds=30, audit=True, action_registry=DEFAULT_ACTIONS)
        return duel, duel.run(), profiles

    def audit_case(self, result, profiles, seed):
        return audit_mental_punch_split(result, profiles, expected_seed=seed,
                                        max_rounds=30, initial_distance=1, ruleset='split_fast_v3')

    def test_current_fast_and_mental_duels_replay_and_audit(self):
        found = set()
        for seed in range(100):
            _, result, profiles = self.run_case(seed)
            self.assertEqual(result, self.run_case(seed)[1])
            self.assertEqual(self.audit_case(result, profiles, seed), [])
            found.update(e['type'] for e in result.log if e['type'] in ('mental_attack', 'fast_use_start'))
        self.assertEqual(found, {'mental_attack', 'fast_use_start'})

    def test_shield_does_not_reduce_focus_damage(self):
        for seed in range(50):
            _, without, profiles = self.run_case(seed, shield=False, wait=True)
            _, with_shield, shield_profiles = self.run_case(seed, shield=True, wait=True)
            a = next(e for e in without.log if e['type'] == 'mental_attack')
            b = next(e for e in with_shield.log if e['type'] == 'mental_attack')
            if a['success']:
                self.assertTrue(any(e['type'] == 'shield_activate' and e.get('trigger') == b['trigger']
                                    for e in with_shield.log))
                self.assertEqual((a['damage_faces'], a['damage'], a['focus_after']),
                                 (b['damage_faces'], b['damage'], b['focus_after']))
                self.assertEqual(b['focus_reduction'], 0)
                self.assertEqual(self.audit_case(without, profiles, seed), [])
                self.assertEqual(self.audit_case(with_shield, shield_profiles, seed), [])
                break
        else:
            self.fail('No successful first Mental Punch')

    def test_shattered_is_a_loss_even_at_positive_health_and_heroic_floor_is_separate(self):
        for seed in range(50):
            _, result, profiles = self.run_case(seed, focus=15, wait=True)
            if result.final_focus[0] <= -15:
                self.assertGreater(result.final_health[0], 0)
                self.assertEqual((result.outcome, result.winner), ('win', profiles[1].name))
                self.assertEqual(self.audit_case(result, profiles, seed), [])
                _, held_back, held_profiles = self.run_case(seed, focus=15, wait=True, heroic_foe=True)
                self.assertGreaterEqual(held_back.final_focus[0], -14)
                self.assertEqual(self.audit_case(held_back, held_profiles, seed), [])
                break
        else:
            self.fail('No Shattered example')

    def test_demoralized_adds_trouble_to_each_fast_limb(self):
        for seed in range(1500):
            _, result, profiles = self.run_case(seed, focus=60)
            focus = profiles[0].max_focus
            for event in result.log:
                if event['type'] == 'mental_attack' and event['target'] == profiles[0].name:
                    focus = event['focus_after']
                if event['type'] == 'fast_limb_check' and focus <= 0:
                    self.assertEqual(event['troubles'], 1)
                    self.assertEqual(self.audit_case(result, profiles, seed), [])
                    return
        self.fail('No demoralized Fast example')

    def test_auditor_rejects_forged_focus_damage_roll_and_stun_timing(self):
        for seed in range(100):
            _, result, profiles = self.run_case(seed, wait=True)
            found = next((i for i, e in enumerate(result.log)
                          if e['type'] == 'mental_attack' and e['success'] and e['fantastic']), None)
            if found is not None:
                break
        self.assertIsNotNone(found)
        self.assertEqual(self.audit_case(result, profiles, seed), [])
        for field, value in (('focus_after', 90), ('focus_reduction', 2), ('calculated_damage', 999),
                             ('total', 999), ('shattered', True)):
            rows = deepcopy(list(result.log)); rows[found][field] = value
            self.assertTrue(self.audit_case(replace(result, log=tuple(rows)), profiles, seed), field)
        rows = deepcopy(list(result.log))
        rows[found + 1]['source_turn_count'] += 1
        self.assertTrue(self.audit_case(replace(result, log=tuple(rows)), profiles, seed))

    def test_rejects_unimplemented_mental_attacker_variants(self):
        altered = replace(self.foe, melee_bonus=1, powers=self.foe.powers | {'mighty'})
        policies = (MentalPunchPolicy('hero'), MentalPunchPolicy('foe', prefer_mental_punch=True))
        with self.assertRaises(ValueError):
            MentalPunchSplitDuel((self.victor, altered), policies, seed=1, audit=True)
        with self.assertRaises(ValueError):
            MentalPunchSplitDuel((self.victor, self.foe), policies, seed=1, audit=True,
                                 stack_stunned_edge=True)
        for changes in ({'powers': self.foe.powers | {'unknown_power'}},
                        {'traits': frozenset({'unknown_trait'})}, {'ranged_range': 10}):
            with self.assertRaises(ValueError):
                MentalPunchSplitDuel((self.victor, replace(self.foe, **changes)), policies, seed=1, audit=True)

    def test_auditor_rejects_forged_fast_edges_and_missing_mental_miss_trigger(self):
        for seed in range(100):
            _, result, profiles = self.run_case(seed)
            fast = next((i for i, e in enumerate(result.log) if e['type'] == 'fast_limb_check'), None)
            miss = next((i for i, e in enumerate(result.log)
                         if e['type'] == 'mental_attack' and not e['success']), None)
            if fast is not None and miss is not None:
                break
        self.assertIsNotNone(fast)
        self.assertIsNotNone(miss)
        rows = deepcopy(list(result.log)); rows[fast]['edges'] += 1
        self.assertTrue(self.audit_case(replace(result, log=tuple(rows)), profiles, seed))
        rows = deepcopy(list(result.log)); rows[miss + 1]['source'] = 'wrong source'
        self.assertTrue(self.audit_case(replace(result, log=tuple(rows)), profiles, seed))
