import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.nonlethal_demo import run
from scripts.verify_sources import ROOT


class NonlethalDemoTests(unittest.TestCase):
    def test_comparison_preserves_both_audited_boundaries(self):
        with TemporaryDirectory() as directory, patch('scripts.nonlethal_demo.source_commit', return_value='test'):
            path = Path(directory) / 'example.json'
            run(path)
            record = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(record['schema'], 'blacklight-experimental-nonlethal-demo-v1')
            self.assertEqual(record['baseline']['final_health'], [100, -19])
            self.assertEqual(record['experimental']['final_health'], [100, 0])
            self.assertEqual(record['audit_issues'], [])
            with self.assertRaises((FileExistsError, ValueError)):
                run(path)

    def test_experimental_comparison_cannot_enter_certified_inventory(self):
        with self.assertRaises(ValueError):
            run(ROOT / 'results' / 'forbidden-nonlethal.json')
