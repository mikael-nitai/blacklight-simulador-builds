import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.ram_checkpoint_demo import SEED, run
from scripts.verify_sources import ROOT


class RamCheckpointDemoTests(unittest.TestCase):
    def test_writes_audited_experimental_checkpoint(self):
        with TemporaryDirectory() as directory, patch('scripts.ram_checkpoint_demo.source_commit', return_value='test'):
            path = Path(directory) / 'checkpoint.json'
            run(path)
            record = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(record['schema'], 'blacklight-experimental-ram-checkpoint-demo-v1')
            self.assertEqual(record['seed'], SEED)
            self.assertEqual(record['audit_issues'], [])
            self.assertEqual(record['status'], 'resolved_checkpoint')
            self.assertEqual(record['log'][-1]['transaction']['parameters']['self_pool'], 'separate')
            with self.assertRaises((FileExistsError, ValueError)):
                run(path)

    def test_experimental_output_cannot_be_placed_in_certified_results(self):
        with self.assertRaises(ValueError):
            run(ROOT / 'results' / 'forbidden-checkpoint.json')
