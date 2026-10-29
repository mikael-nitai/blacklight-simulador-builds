import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.ram_incapacity_demo import run
from scripts.verify_sources import ROOT


class RamIncapacityDemoTests(unittest.TestCase):
    def test_hypotheses_remain_distinct_and_reject_overwrite(self):
        with TemporaryDirectory() as directory, patch('scripts.ram_incapacity_demo.source_commit', return_value='test'):
            path = Path(directory) / 'comparison.json'
            run(path)
            payload = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(payload['schema'], 'blacklight-experimental-ram-incapacity-demo-v1')
            self.assertEqual(payload['results']['lethal_impact']['outcome'], 'draw')
            self.assertEqual(payload['results']['nonlethal_impact']['winner'], 'Attacker')
            with self.assertRaises((FileExistsError, ValueError)):
                run(path)

    def test_certified_inventory_is_not_a_permitted_destination(self):
        with self.assertRaises(ValueError):
            run(ROOT / 'results' / 'forbidden-ram-incapacity.json')
