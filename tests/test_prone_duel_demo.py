import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.prone_duel_demo import SEED, run
from scripts.verify_sources import ROOT


class ProneDuelDemoTests(unittest.TestCase):
    def test_audited_demo_is_experimental_and_cannot_overwrite(self):
        with TemporaryDirectory() as directory, patch('scripts.prone_duel_demo.source_commit', return_value='test'):
            path = Path(directory) / 'demo.json'
            run(path)
            payload = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(payload['schema'], 'blacklight-experimental-prone-duel-demo-v1')
            self.assertEqual(payload['seed'], SEED)
            self.assertEqual(payload['initial_prone'], [False, True])
            self.assertEqual(payload['audit_issues'], [])
            self.assertTrue(any(event['type'] == 'prone_check' for event in payload['result']['log']))
            with self.assertRaises((FileExistsError, ValueError)):
                run(path)

    def test_cannot_write_to_certified_inventory(self):
        with self.assertRaises(ValueError):
            run(ROOT / 'results' / 'forbidden-prone-demo.json')
