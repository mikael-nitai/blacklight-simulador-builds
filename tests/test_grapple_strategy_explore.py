from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.audit_grapple_strategy_explore import audit
from scripts.grapple_strategy_explore import policies_for, run, seed_for
from scripts.replay_grapple_strategy_explore import replay


class GrappleStrategyExploreTests(unittest.TestCase):
    def test_seed_and_predeclared_policies(self):
        self.assertEqual(seed_for(0), seed_for(0))
        self.assertNotEqual(seed_for(0), seed_for(1))
        with self.assertRaises(ValueError):
            seed_for(1000)
        q, escaping = policies_for('escape')
        _, attacking = policies_for('attack')
        self.assertTrue(q.prefer_grapple and q.attack_when_grabbing and escaping.escape_reaction)
        self.assertFalse(escaping.attack_when_grabbed)
        self.assertFalse(attacking.escape_reaction)
        self.assertTrue(attacking.attack_when_grabbed)

    def test_eight_cell_accounting_and_sample_replay_detect_tampering(self):
        with TemporaryDirectory() as directory, \
                patch('scripts.grapple_strategy_explore.source_commit', return_value='test'), \
                patch('scripts.grapple_strategy_explore.audit', side_effect=lambda p: audit(p, verify_snapshots=False)), \
                patch('scripts.replay_grapple_strategy_explore.audit', side_effect=lambda p: audit(p, verify_snapshots=False)):
            dataset = Path(directory) / 'small.json'
            replay_path = Path(directory) / 'replay.json'
            run(dataset, n=2)
            data = json.loads(dataset.read_text(encoding='utf-8'))
            self.assertFalse(data['matches_preregistration'])
            self.assertEqual(audit(data, verify_snapshots=False), [])
            self.assertEqual(len(data['cells']), 8)
            self.assertIn('Close attacks and miss reactions between the two held actors are modeled.',
                          data['crossbones_subset']['assumptions'])
            self.assertNotIn('The grapple host restricts actors in a hold to escape, release or wait.',
                             data['crossbones_subset']['assumptions'])
            replay(dataset, replay_path)
            self.assertEqual(len(json.loads(replay_path.read_text(encoding='utf-8'))['checked']), 16)
            for mutate in ('seed', 'wilson', 'count', 'policy', 'sources', 'powers', 'profile', 'nan'):
                with self.subTest(mutate=mutate):
                    altered = deepcopy(data)
                    cell = altered['cells'][0]
                    if mutate == 'seed':
                        cell['records'][0]['seed'] += 1
                    elif mutate == 'wilson':
                        cell['summary']['victory_wilson_95'][0] += 0.1
                    elif mutate == 'count':
                        cell['summary']['counts']['victory'] += 1
                    elif mutate == 'policy':
                        cell['policies'][1]['escape_reaction'] = False
                    elif mutate == 'sources':
                        del altered['source_sha256']['experimental/grappling_duel.py']
                    elif mutate == 'powers':
                        altered['crossbones_subset']['profile']['powers'] = None
                    elif mutate == 'profile':
                        altered['crossbones_subset']['profile']['melee_defense'] = 999
                    else:
                        cell['summary']['victory_wilson_95'][0] = float('nan')
                    self.assertTrue(audit(altered, verify_snapshots=False))
            rows = data['cells'][0]['records']
            rows[0]['result_sha256'] = '0' * 64
            dataset.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaisesRegex(RuntimeError, 'Replay mismatch'):
                replay(dataset, Path(directory) / 'tampered.json')
            before = replay_path.read_bytes()
            with self.assertRaises((FileExistsError, ValueError)):
                replay(dataset, replay_path)
            self.assertEqual(replay_path.read_bytes(), before)
