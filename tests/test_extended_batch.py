"""Independent checks for optional per-start physical-duel batch samples."""

from copy import deepcopy
from math import sqrt
from pathlib import Path
from statistics import mean, stdev
import unittest
from unittest.mock import patch

from blacklight.batch_audit import audit_batch_metadata
from blacklight.engine import Duel
from combatants.runner import run_batch, run_duel
from combatants.sheets import load_sheet
from combatants.split_fast import SplitFastPolicy
from scripts.freeze_results import require_generic_provenance


ROOT = Path(__file__).resolve().parents[1]
VICTOR = ROOT / 'characters/victor_halle/rank3_2026-10-27_split_fast.json'
OPPONENT = ROOT / 'characters/examples/synthetic_rank4_split_fast.json'


class TestExtendedBatch(unittest.TestCase):
    def setUp(self):
        self.hero = load_sheet(VICTOR)
        self.opponent = load_sheet(OPPONENT)
        self.hero_policy = SplitFastPolicy('hero', weapon='hammer', offhand='blade',
                                           prefer_fast=True, effect_limb=1, shield_react=True)
        self.enemy_policy = SplitFastPolicy('enemy')

    def batch(self, *, n=5, extended=True, **kwargs):
        return run_batch(self.hero, self.opponent, self.hero_policy, self.enemy_policy,
                         n=n, master_seed=782, max_rounds=6,
                         extended_metrics=extended, **kwargs)

    def test_sample_replays_against_complete_audited_duels(self):
        batch = self.batch()
        self.assertEqual(audit_batch_metadata(batch), [])
        fields = batch['extended_fields']
        for sample, trace in zip(batch['extended_samples_all_starts'], batch['audited_traces']):
            row = dict(zip(fields, sample))
            duel = run_duel(self.hero, self.opponent, self.hero_policy, self.enemy_policy,
                            seed=trace['seed'], max_rounds=6)
            result = duel['result']
            self.assertEqual(row['seed'], trace['seed'])
            self.assertEqual(row['outcome'], duel['hero_outcome'])
            self.assertEqual((row['rounds'], row['turns']), (result['rounds'], result['turns']))
            self.assertEqual((row['final_health'], row['opponent_final_health']), tuple(result['final_health']))
            self.assertEqual((row['final_focus'], row['opponent_final_focus']), tuple(result['final_focus']))
            for key, value in result['metrics'][0].items():
                self.assertEqual(row[key], value)

    def test_manual_mean_error_and_nearest_rank_quantiles(self):
        payload = self.batch(n=3)
        field = 'damage_mitigated'
        column = payload['extended_fields'].index(field)
        # The values are deliberately hand-chosen; no engine calculation is
        # used to obtain their mean, sample-standard error, or quantiles.
        for row, value in zip(payload['extended_samples_all_starts'], (2, 4, 9)):
            row[column] = value
        payload['extended_metrics_all_starts'][field] = {
            'mean': 5, 'mc_se': sqrt(13 / 3), 'q10': 2, 'q50': 4, 'q90': 9}
        # This proves arithmetic consistency, not origin of the fabricated samples.
        self.assertEqual(audit_batch_metadata(payload), [])
        payload['extended_metrics_all_starts'][field]['q50'] = 9
        self.assertTrue(any('q50' in issue for issue in audit_batch_metadata(payload)))

    def test_recording_does_not_change_seed_identity_or_legacy_output(self):
        normal, extended = self.batch(extended=False), self.batch(extended=True)
        for key in ('cell_sha256', 'seed_formula', 'audited_traces', 'outcomes', 'rates',
                    'metrics_all_starts', 'source_sha256', 'mechanics_contract_sha256'):
            with self.subTest(field=key):
                self.assertEqual(normal[key], extended[key])
        self.assertNotIn('extended_samples_all_starts', normal)
        self.assertEqual(audit_batch_metadata(normal), [])

    def test_single_start_quantiles_and_options(self):
        payload = self.batch(n=1)
        self.assertEqual(audit_batch_metadata(payload), [])
        for field, summary in payload['extended_metrics_all_starts'].items():
            row = dict(zip(payload['extended_fields'], payload['extended_samples_all_starts'][0]))
            self.assertIsNone(summary['mc_se'])
            self.assertEqual((summary['q10'], summary['q50'], summary['q90']), (row[field],) * 3)
        with self.assertRaises(ValueError):
            self.batch(extended=True, audit_every=2)
        for invalid in (1, None, 'true'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.batch(extended=invalid)

    def test_single_field_forgeries_and_freeze_gate_reject(self):
        original = self.batch()
        positions = {name: original['extended_fields'].index(name)
                     for name in original['extended_fields']}
        mutations = ('schema', 'missing', 'seed', 'index', 'bool', 'outcome',
                     'health', 'focus', 'hits', 'fantastic', 'ripostes', 'damage_horizon',
                     'summary_mean', 'summary_se', 'summary_q90', 'aggregate')
        for mutation in mutations:
            payload = deepcopy(original)
            sample = payload['extended_samples_all_starts'][0]
            summary = payload['extended_metrics_all_starts']
            if mutation == 'schema':
                payload['extended_metrics_schema'] = 'unrecognized'
            elif mutation == 'missing':
                payload['extended_samples_all_starts'].pop()
            elif mutation == 'seed':
                sample[positions['seed']] += 1
            elif mutation == 'index':
                sample[positions['index']] = 2
            elif mutation == 'bool':
                sample[positions['turns']] = True
            elif mutation == 'outcome':
                sample[positions['outcome']] = 'draw' if sample[positions['outcome']] != 'draw' else 'win'
            elif mutation == 'health':
                sample[positions['final_health']] += 1
            elif mutation == 'focus':
                sample[positions['final_focus']] += 1
            elif mutation == 'hits':
                sample[positions['hits']] = sample[positions['attacks']] + 1
            elif mutation == 'fantastic':
                sample[positions['fantastic_hits']] = sample[positions['hits']] + 1
            elif mutation == 'ripostes':
                sample[positions['ripostes']] = sample[positions['attacks']] + 1
            elif mutation == 'damage_horizon':
                sample[positions['damage_round3']] = sample[positions['damage_dealt']] + 1
            elif mutation == 'summary_mean':
                summary['damage_dealt']['mean'] += 1
            elif mutation == 'summary_se':
                summary['damage_dealt']['mc_se'] = -1
            elif mutation == 'summary_q90':
                summary['damage_dealt']['q90'] += 1
            elif mutation == 'aggregate':
                payload['metrics_all_starts']['hero_damage_dealt']['mean'] += 1
            with self.subTest(mutation=mutation):
                self.assertTrue(audit_batch_metadata(payload))
                with self.assertRaisesRegex(ValueError, 'Generic batch audit'):
                    require_generic_provenance(payload, ROOT, 'HEAD')

    def test_corrupted_fighter_summary_stops_before_sample_is_published(self):
        original = Duel._finish
        def forged(battle, *args):
            from dataclasses import replace
            result = original(battle, *args)
            metrics = deepcopy(result.metrics)
            metrics[0]['hits'] += 1
            return replace(result, metrics=metrics)
        with patch.object(Duel, '_finish', forged), self.assertRaisesRegex(RuntimeError, 'result metric mismatch'):
            self.batch(n=1)

    def test_coordinated_forged_action_or_turn_counts_are_rejected(self):
        original = self.batch()
        positions = {name: original['extended_fields'].index(name)
                     for name in original['extended_fields']}
        for field in ('turns', 'blade_bonus_actions', 'stuns_applied'):
            payload = deepcopy(original)
            samples = payload['extended_samples_all_starts']
            row = samples[0]
            row[positions[field]] = (1_000_000_000 if field == 'turns' else
                                     row[positions['fantastic_hits']] + 1)
            values = sorted(row[positions[field]] for row in samples)
            # Independent recomputation simulates a coordinated falsification;
            # a consistency-only checker would otherwise accept this payload.
            payload['extended_metrics_all_starts'][field] = {
                'mean': mean(values), 'mc_se': stdev(values) / sqrt(len(values)),
                'q10': values[0], 'q50': values[2], 'q90': values[4]}
            with self.subTest(field=field):
                self.assertTrue(audit_batch_metadata(payload))

    def test_zero_focus_is_rejected_even_with_coordinated_summaries(self):
        original = self.batch()
        positions = {name: original['extended_fields'].index(name)
                     for name in original['extended_fields']}
        for field in ('final_focus', 'opponent_final_focus'):
            payload = deepcopy(original)
            samples = payload['extended_samples_all_starts']
            samples[0][positions[field]] = 0
            if field == 'final_focus':
                samples[0][positions['focus_spent']] = self.hero.resources['focus']
            changed = (field, 'focus_spent') if field == 'final_focus' else (field,)
            for changed_field in changed:
                values = sorted(row[positions[changed_field]] for row in samples)
                payload['extended_metrics_all_starts'][changed_field] = {
                    'mean': mean(values), 'mc_se': stdev(values) / sqrt(len(values)),
                    'q10': values[0], 'q50': values[2], 'q90': values[4]}
            if field == 'final_focus':
                summary = payload['extended_metrics_all_starts']['final_focus']
                payload['metrics_all_starts']['hero_final_focus'] = {
                    'mean': summary['mean'], 'mc_se': summary['mc_se']}
            with self.subTest(field=field):
                self.assertIn('extended batch resource mismatch at sample 0', audit_batch_metadata(payload))


if __name__ == '__main__':
    unittest.main()
