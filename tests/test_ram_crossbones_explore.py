from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest
from unittest.mock import MagicMock, patch

from blacklight.engine import IllegalAction, Profile
from experimental.stopping_duel import StoppingPolicy
from scripts.audit_ram_crossbones_explore import audit
from scripts.ram_crossbones_explore import (N_PER_CELL, StationaryPolicy, policies_for, run,
                                             seed_for, simulate, summarize)


class RamCrossbonesExploreTests(unittest.TestCase):
    def test_seed_domains_and_policy_configuration(self):
        self.assertNotEqual(seed_for('stationary', 0), seed_for('kite', 0))
        self.assertEqual(seed_for('stationary', 0), seed_for('stationary', 0))
        with self.assertRaises(ValueError):
            seed_for('stationary', N_PER_CELL)
        foe, hero = policies_for('kite', 'fast_blade', True)
        self.assertTrue(foe.kite and foe.prefer_stopping and hero.use_ram)
        self.assertEqual((hero.effect_limb, hero.weapon, hero.offhand), (1, 'hammer', 'blade'))

    def test_summary_bounds_include_unresolved_as_unknown(self):
        summary = summarize([{'status': 'victory'}, {'status': 'defeat'},
                             {'status': 'unresolved_death_threshold'}, {'status': 'inconclusive'}])
        self.assertEqual(summary['victory_identification_bounds'], [0.25, 0.5])
        self.assertEqual(summary['counts']['unresolved_death_threshold'], 1)

    def test_other_illegal_actions_are_never_counted_as_unresolved(self):
        battle = MagicMock()
        battle.run.side_effect = IllegalAction('unexpected illegal action')
        with patch('scripts.ram_crossbones_explore.StoppingRamDuel', return_value=battle):
            with self.assertRaisesRegex(IllegalAction, 'unexpected illegal action'):
                simulate((MagicMock(), MagicMock()), (MagicMock(), MagicMock()), 'generic', 1)

    def test_sample_execution_and_independent_accounting_tamper_checks(self):
        with TemporaryDirectory() as directory, \
                patch('scripts.ram_crossbones_explore.source_commit', return_value='test'), \
                patch('scripts.ram_crossbones_explore.audit_exploration', return_value=[]):
            output = Path(directory) / 'small.json'
            run(output, n=2)
            data = json.loads(output.read_text(encoding='utf-8'))
            self.assertFalse(data['matches_preregistration'])
            self.assertEqual(len(data['cells']), 12)
            self.assertEqual(audit(data, verify_snapshots=False), [])
            altered = deepcopy(data)
            altered['cells'][0]['records'][0]['seed'] += 1
            self.assertTrue(audit(altered, verify_snapshots=False))
            altered = deepcopy(data)
            altered['cells'][0]['summary']['recorded_victory_wilson_95'][0] += 0.01
            self.assertTrue(audit(altered, verify_snapshots=False))
            altered = deepcopy(data)
            altered['cells'][0]['summary']['counts']['victory'] += 1
            self.assertTrue(audit(altered, verify_snapshots=False))
            altered = deepcopy(data)
            altered['cells'][0]['policies'][1]['shield_react'] = False
            self.assertTrue(audit(altered, verify_snapshots=False))
            altered = deepcopy(data)
            completed = next(row for row in altered['cells'][0]['records']
                             if row['status'] != 'unresolved_death_threshold')
            completed['victor_metrics']['damage_taken'] += 1
            self.assertTrue(audit(altered, verify_snapshots=False))
            prior = output.read_bytes()
            with self.assertRaises((FileExistsError, ValueError)):
                run(output, n=2)
            self.assertEqual(output.read_bytes(), prior)

    def test_unresolved_is_explicit_and_reproducible(self):
        target = Profile('Target', 3, 250, 60, 2, 0, 5, 2, 12, 10, 5, initiative_modifier=0)
        hero = Profile('Hero', 3, 1, 60, 4, 0, 5, 2, 14, 10, 5, initiative_modifier=100,
                       powers=frozenset({'healing_factor'}))
        policies = (StationaryPolicy('target', always_wait=True, use_ram=False), StoppingPolicy('hero'))
        unresolved = None
        for seed in range(30):
            candidate = simulate((target, hero), policies, 'generic', seed)
            if candidate['status'] == 'unresolved_death_threshold':
                unresolved = candidate
                break
        self.assertIsNotNone(unresolved)
        self.assertLessEqual(unresolved['raw_health_after'], unresolved['death_threshold'])
        self.assertEqual(unresolved, simulate((target, hero), policies, 'generic', seed))
