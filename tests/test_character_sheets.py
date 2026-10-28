"""Sheet substitution, coverage rejection and legacy-engine equivalence."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from blacklight.engine import Duel, blacklight_profile
from blacklight.policies import ATTACK, SHIELD_BLADE_HAMMER_REACTIVE
from combatants import load_sheet, compile_duel, coverage, CoverageError
from combatants.runner import run_duel, run_batch
from combatants.sheets import parse_sheet, sheet_record


ROOT = Path(__file__).resolve().parents[1]
VICTOR = ROOT / 'characters/victor_halle/rank3_2026-10-26.json'
RANK4 = ROOT / 'characters/examples/synthetic_rank4.json'


class TestCharacterSheets(unittest.TestCase):
    def test_six_abilities_and_sources_survive_loading(self):
        sheet = load_sheet(VICTOR)
        self.assertEqual((sheet.abilities['ego'], sheet.abilities['logic']), (1, 0))
        self.assertEqual((sheet.rank, sheet.resources['focus']), (3, 90))
        self.assertEqual(sheet.level('mighty'), 3)
        self.assertEqual(sheet.provenance[0]['sha256'],
                         '6c907dfcaa2af39b904e6144466915bafc6b6f66f407aeb312dea112fd3200d1')
        self.assertTrue(all(feature.sources for feature in sheet.features))
        with self.assertRaises(TypeError):
            sheet.abilities['melee'] = 99

    def test_loaded_victor_replays_existing_engine_exactly(self):
        loaded = compile_duel(load_sheet(VICTOR))
        old = blacklight_profile()
        foe = replace(old, name='Opponent')
        policies = (SHIELD_BLADE_HAMMER_REACTIVE, ATTACK)
        for seed in range(20):
            expected = Duel((old, foe), policies, seed=seed, audit=True).run()
            actual = Duel((loaded, foe), policies, seed=seed, audit=True).run()
            self.assertEqual(actual, expected)

    def test_rank4_other_character_needs_no_engine_change(self):
        sheet = load_sheet(RANK4)
        profile = compile_duel(sheet)
        self.assertEqual((profile.rank, profile.max_health, profile.melee,
                          profile.melee_bonus, profile.health_dr),
                         (4, 180, 7, 2, 1))
        result = run_duel(sheet, load_sheet(VICTOR), ATTACK, ATTACK, seed=402)
        self.assertEqual(result['audit_issues'], [])
        self.assertIn(result['hero_outcome'], ('win', 'loss', 'draw', 'inconclusive'))
        self.assertEqual(result['hero_id'], 'synthetic_rank4_example')
        if result['result']['winner'] is not None:
            self.assertEqual(result['hero_outcome'] == 'win',
                             result['result']['winner'] == sheet.name)
        self.assertEqual(load_sheet(VICTOR).rank, 3)

    def test_unknown_power_is_retained_and_blocks_simulation(self):
        data = json.loads(VICTOR.read_text(encoding='utf-8'))
        data['features'].append({'id': 'teleport_future_example', 'kind': 'power',
                                 'level': 2, 'parameters': {},
                                 'sources': ['Example only']})
        sheet = parse_sheet(data)
        self.assertEqual(sheet.level('teleport_future_example'), 2)
        report = coverage(sheet)
        self.assertFalse(report['ready_for_this_scope'])
        with self.assertRaises(CoverageError):
            compile_duel(sheet)

    def test_rank4_shield_cannot_silently_reuse_rank3_effect(self):
        data = json.loads(VICTOR.read_text(encoding='utf-8'))
        data['rank'] = 4
        with self.assertRaisesRegex(CoverageError, 'reflection'):
            compile_duel(parse_sheet(data))

    def test_official_defense_variation_is_preserved_and_flagged(self):
        data = json.loads(RANK4.read_text(encoding='utf-8'))
        data['defenses']['agility'] = 14
        sheet = parse_sheet(data)
        self.assertEqual(sheet.defenses['agility'], 14)
        with self.assertRaisesRegex(CoverageError, 'Modified agility defense'):
            compile_duel(sheet)

    def test_duplicate_power_levels_and_unknown_fields_are_rejected(self):
        data = json.loads(VICTOR.read_text(encoding='utf-8'))
        duplicate = deepcopy(data)
        duplicate['features'].append(deepcopy(duplicate['features'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate feature'):
            parse_sheet(duplicate)
        data['rankk'] = data['rank']
        with self.assertRaises(ValueError):
            parse_sheet(data)

    def test_unimplemented_parameter_variation_blocks_adapter(self):
        data = json.loads(RANK4.read_text(encoding='utf-8'))
        data['features'][0]['parameters'] = {'custom_bonus': 99}
        with self.assertRaisesRegex(CoverageError, 'parameter variation'):
            compile_duel(parse_sheet(data))

    def test_official_damage_ruleset_is_not_silently_mixed_with_table(self):
        data = json.loads(RANK4.read_text(encoding='utf-8'))
        data['ruleset'] = 'official_core_d616'
        with self.assertRaisesRegex(CoverageError, 'ruleset'):
            compile_duel(parse_sheet(data))

    def test_sheet_roundtrip_and_nested_source_data_are_immutable(self):
        data = json.loads(VICTOR.read_text(encoding='utf-8'))
        sheet = parse_sheet(data)
        data['provenance'][2]['paths'].append('injected after import')
        self.assertNotIn('injected after import', sheet.provenance[2]['paths'])
        self.assertEqual(parse_sheet(sheet_record(sheet)), sheet)

    def test_generic_batch_is_reproducible_and_counts_all_outcomes(self):
        hero, foe = load_sheet(RANK4), load_sheet(VICTOR)
        args = dict(n=20, master_seed=812, audit_every=1)
        first = run_batch(hero, foe, ATTACK, ATTACK, **args)
        self.assertEqual(first, run_batch(hero, foe, ATTACK, ATTACK, **args))
        self.assertEqual(sum(first['outcomes'].values()), 20)
        self.assertEqual(len(first['audited_traces']), 20)
        self.assertTrue(all(not row['issues'] for row in first['audited_traces']))
        self.assertEqual(first['sheets'][0]['name'], 'Exemplo Rank 4')

    def test_odd_fast_damage_bonus_is_blocked_before_any_fight(self):
        data = json.loads(RANK4.read_text(encoding='utf-8'))
        data['features'].append({'id': 'fast_strikes', 'kind': 'power',
                                 'level': 1, 'parameters': {},
                                 'sources': ['Synthetic coverage test']})
        with self.assertRaisesRegex(CoverageError, 'rounding ruling'):
            compile_duel(parse_sheet(data))

    def test_negative_healing_factor_is_blocked_without_inventing_a_rule(self):
        data = json.loads(VICTOR.read_text(encoding='utf-8'))
        data['abilities']['resilience'] = -1
        data['defenses']['resilience'] = 9
        sheet = parse_sheet(data)
        self.assertFalse(coverage(sheet)['ready_for_this_scope'])
        with self.assertRaisesRegex(CoverageError, 'negative Resilience'):
            compile_duel(sheet)
        with self.assertRaisesRegex(ValueError, 'negative Resilience'):
            replace(blacklight_profile(), resilience=-1)
        data['features'] = [row for row in data['features'] if row['id'] != 'healing_factor']
        self.assertEqual(compile_duel(parse_sheet(data)).resilience, -1)
        data['abilities']['resilience'] = 0
        data['defenses']['resilience'] = 10
        original = json.loads(VICTOR.read_text(encoding='utf-8'))
        data['features'].append(next(row for row in original['features'] if row['id'] == 'healing_factor'))
        self.assertEqual(compile_duel(parse_sheet(data)).resilience, 0)

    def test_blade_rank_requirement_is_checked_at_adapter(self):
        data = json.loads(VICTOR.read_text(encoding='utf-8'))
        data['rank'] = 1
        with self.assertRaisesRegex(CoverageError, 'requires Rank 2'):
            compile_duel(parse_sheet(data))

    def test_direct_runner_binds_rule_parameters_and_source_hashes(self):
        from hashlib import sha256
        result = run_duel(load_sheet(RANK4), load_sheet(VICTOR), ATTACK, ATTACK, seed=402)
        self.assertEqual(result['execution_adapter'], 'modular_physical_duel_v3')
        self.assertTrue(result['runtime']['python'])
        self.assertTrue(result['runtime']['implementation'])
        modules = {row['kind']: row for row in result['registered_action_modules']}
        self.assertEqual((modules['heal']['minimum_spend'],
                          modules['heal']['maximum_spend_per_rank'],
                          modules['heal']['health_per_focus']), (5, 5, 2))
        self.assertEqual(modules['shield']['requirements'], [{'kind': 'weapon', 'id': 'shield'}])
        self.assertTrue(all('\\' not in key for key in result['source_sha256']))
        for name in ('combatants/actions.py', 'combatants/modular_duel.py', 'combatants/runner.py'):
            # Repository-relative keys are portable across operating systems.
            key = Path(name).as_posix()
            self.assertEqual(result['source_sha256'][key],
                             sha256((ROOT / name).read_bytes()).hexdigest())

    def test_direct_runner_rejects_source_changes_during_execution(self):
        with patch('combatants.runner._source_manifest',
                   side_effect=[{'source': 'before'}, {'source': 'after'}]):
            with self.assertRaisesRegex(RuntimeError, 'sources changed'):
                run_duel(load_sheet(RANK4), load_sheet(VICTOR), ATTACK, ATTACK, seed=402)

    def test_runner_rejects_a_falsified_reaction_capacity(self):
        def faulty_reset(duel):
            for fighter in duel.fighters:
                fighter.reactions = 99
                fighter.reacted_to.clear()
                duel._record('reaction_reset', ('ACT-03', 'ACT-04'),
                             actor=fighter.profile.name, reactions=99)

        with patch.object(Duel, '_reset_reactions_for_round', faulty_reset):
            with self.assertRaisesRegex(RuntimeError, 'reaction budget'):
                run_duel(load_sheet(RANK4), load_sheet(VICTOR), ATTACK, ATTACK, seed=402)


if __name__ == '__main__':
    unittest.main()
