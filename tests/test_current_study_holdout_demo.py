from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.current_study_holdout_demo import CASES, demonstration


class DemonstrationTests(unittest.TestCase):
    def test_each_trace_is_audited_and_uses_fixed_seed(self):
        with TemporaryDirectory() as directory, patch('scripts.current_study_holdout_demo.source_commit', return_value='test'):
            for scenario, seed in CASES.items():
                with self.subTest(scenario=scenario):
                    path = Path(directory) / f'{scenario}.json'
                    result = demonstration(scenario, path)
                    self.assertEqual(result['seed'], seed)
                    self.assertEqual(result['audit_issues'], [])
                    self.assertTrue(result['result']['log'])
                    self.assertIn('not a statistical sample', result['demonstration']['purpose'])
                    with self.assertRaises((FileExistsError, ValueError)):
                        demonstration(scenario, path)

    def test_unknown_scenario_rejected(self):
        with self.assertRaises(ValueError):
            demonstration('unknown', 'ignored.json')
