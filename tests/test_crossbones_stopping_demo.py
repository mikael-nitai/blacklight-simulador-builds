import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from scripts.crossbones_stopping_demo import run


class CrossbonesStoppingDemoTests(TestCase):
    def test_audited_example_lists_missing_powers_and_preserves_output(self):
        with TemporaryDirectory() as directory, patch('scripts.crossbones_stopping_demo.source_commit', return_value='test'):
            output = Path(directory) / 'example.json'
            run(output)
            data = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(data['audit_issues'], [])
            self.assertIn('Stopping Power', data['crossbones_subset']['included_powers'])
            self.assertIn('Weapons Blazing', data['crossbones_subset']['omitted_powers'])
            self.assertTrue(any(e.get('stopping_role') == 'followup' for e in data['result']['log']))
            original = output.read_bytes()
            with self.assertRaises((FileExistsError, ValueError)):
                run(output)
            self.assertEqual(output.read_bytes(), original)
