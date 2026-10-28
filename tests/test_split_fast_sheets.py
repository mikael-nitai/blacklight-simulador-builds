"""Versioned character records select the new table engine without changing Rank."""

from dataclasses import replace
import unittest
from pathlib import Path
from unittest.mock import patch

from blacklight.policies import ATTACK, BLADE_HAMMER_FAST
from combatants import compile_duel, coverage, load_sheet
from combatants.modular_duel import ModularDuel
from combatants.runner import run_batch, run_duel
from combatants.sheets import sheet_record
from combatants.split_fast import SplitFastDuel, SplitFastPolicy


ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'characters/victor_halle/rank3_2026-10-26.json'
CURRENT = ROOT / 'characters/victor_halle/rank3_2026-10-27_split_fast.json'
FOE = ROOT / 'characters/examples/synthetic_rank4_split_fast.json'


class TestSplitFastSheets(unittest.TestCase):
    def test_new_rule_record_preserves_actual_character_values(self):
        old, new = load_sheet(OLD), load_sheet(CURRENT)
        old_data, new_data = sheet_record(old), sheet_record(new)
        for key in old_data.keys() - {'ruleset', 'revision', 'notes'}:
            self.assertEqual(old_data[key], new_data[key], key)
        self.assertEqual(new.rank, 3)
        self.assertEqual(compile_duel(new), compile_duel(old))
        self.assertEqual(coverage(new)['engine'], 'split_fast_physical_duel')

    def test_mixed_table_versions_fail_before_combat(self):
        hero, foe = load_sheet(CURRENT), load_sheet(OLD)
        foe = replace(foe, name='Historical duplicate')
        with self.assertRaisesRegex(ValueError, 'same table ruleset'):
            run_duel(hero, foe, ATTACK, ATTACK, seed=1)

    def test_runner_refuses_a_wrong_engine_for_either_ruleset(self):
        current_hero, current_foe = load_sheet(CURRENT), load_sheet(FOE)
        old_hero = load_sheet(OLD)
        old_foe = replace(old_hero, name='Historical opponent')
        for hero, foe, wrong in ((current_hero, current_foe, ModularDuel),
                                 (old_hero, old_foe, SplitFastDuel)):
            with self.subTest(ruleset=hero.ruleset), \
                    patch('combatants.runner._engine_for', return_value=wrong):
                with self.assertRaisesRegex(RuntimeError, 'engine.*ruleset'):
                    run_duel(hero, foe, ATTACK, ATTACK, seed=51)
                with self.assertRaisesRegex(RuntimeError, 'engine.*ruleset'):
                    run_batch(hero, foe, ATTACK, ATTACK, n=1, master_seed=51)

    def test_a_false_engine_label_cannot_hide_legacy_fast_events(self):
        hero, foe = load_sheet(CURRENT), load_sheet(FOE)
        # A mistaken implementation that reports the new label while executing
        # the old one-check Fast contract must still be rejected by the auditor.
        with patch('combatants.runner._engine_for', return_value=ModularDuel), \
                patch.object(ModularDuel, 'table_ruleset', 'split_fast_v3', create=True):
            with self.assertRaisesRegex(RuntimeError, 'ruleset.*Fast'):
                run_duel(hero, foe, BLADE_HAMMER_FAST, ATTACK, seed=51, max_rounds=5)

    def test_experimental_engine_cannot_use_the_stable_runner(self):
        class ExperimentalDuel(SplitFastDuel):
            execution_scope = 'experimental_group'

        hero, foe = load_sheet(CURRENT), load_sheet(FOE)
        with patch('combatants.runner._engine_for', return_value=ExperimentalDuel):
            with self.assertRaisesRegex(RuntimeError, 'experimental engine'):
                run_duel(hero, foe, ATTACK, ATTACK, seed=51)

    def test_two_choices_work_through_generic_character_api(self):
        hero, foe = load_sheet(CURRENT), load_sheet(FOE)
        for selected in (0, 1):
            policy = SplitFastPolicy('test', weapon='blade', offhand='hammer', prefer_fast=True,
                                      effect_limb=selected, shield_react=True)
            result = run_duel(hero, foe, policy, ATTACK, seed=51, max_rounds=5)
            self.assertEqual(result['execution_adapter'], 'split_fast_physical_duel_v1')
            self.assertEqual(result['table_ruleset'], 'split_fast_v3')
            self.assertTrue(result['fast_zero_dice_bonus'])
            self.assertEqual(result['audit_issues'], [])
            declarations = [e for e in result['result']['log'] if e['type'] == 'fast_use_start']
            self.assertTrue(declarations)
            self.assertTrue(all(e['effect_limb'] == selected for e in declarations))

    def test_rank4_substitution_uses_same_current_engine_and_reproducible_batch(self):
        hero, foe = load_sheet(FOE), load_sheet(CURRENT)
        policy = SplitFastPolicy('victor', weapon='hammer', offhand='blade',
                                  prefer_fast=True, effect_limb=0, shield_react=True)
        first = run_batch(hero, foe, ATTACK, policy, n=12, master_seed=731,
                           max_rounds=5, audit_every=1)
        second = run_batch(hero, foe, ATTACK, policy, n=12, master_seed=731,
                            max_rounds=5, audit_every=1)
        self.assertEqual(first, second)
        self.assertEqual(sum(first['outcomes'].values()), 12)
        self.assertEqual(len(first['audited_traces']), 12)
        self.assertEqual(first['sheets'][0]['rank'], 4)
        self.assertEqual(first['execution_adapter'], 'split_fast_physical_duel_v1')


if __name__ == '__main__':
    unittest.main()
