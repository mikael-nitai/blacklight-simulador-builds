import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.ram_prone_demo import SEED, run
from scripts.verify_sources import ROOT


class RamProneDemoTests(unittest.TestCase):
    def test_audited_full_duel_is_experimental_and_no_overwrite(self):
        with TemporaryDirectory() as directory, patch('scripts.ram_prone_demo.source_commit', return_value='test'):
            path = Path(directory) / 'demo.json'
            run(path)
            payload = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(payload['schema'], 'blacklight-experimental-ram-prone-duel-demo-v1')
            self.assertEqual(payload['seed'], SEED)
            self.assertEqual(payload['audit_issues'], [])
            self.assertTrue(any(event['type'] == 'ram_attack' for event in payload['result']['log']))
            self.assertTrue(any(event['type'] == 'turn_end' for event in payload['result']['log']))
            with self.assertRaises((FileExistsError, ValueError)):
                run(path)

    def test_certified_inventory_is_not_a_permitted_destination(self):
        with self.assertRaises(ValueError):
            run(ROOT / 'results' / 'forbidden-ram-prone-demo.json')
