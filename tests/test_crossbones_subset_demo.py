import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from scripts.crossbones_subset_demo import run


class CrossbonesSubsetDemoTests(TestCase):
    def test_demo_has_audit_omissions_and_no_overwrite(self):
        with TemporaryDirectory() as directory, patch('scripts.crossbones_subset_demo.source_commit', return_value='test'):
            output = Path(directory) / 'example.json'
            run(output)
            payload = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(payload['audit_issues'], [])
            self.assertEqual(payload['seed'], 30)
            self.assertIn('Fast Hands', payload['crossbones_subset']['omitted_powers'])
            self.assertIn('Villainous', payload['crossbones_subset']['omitted_tags'])
            self.assertEqual(payload['ranged_weapons'], ['submachine_gun', 'generic'])
            original = output.read_bytes()
            with self.assertRaises((FileExistsError, ValueError)):
                run(output)
            self.assertEqual(output.read_bytes(), original)
