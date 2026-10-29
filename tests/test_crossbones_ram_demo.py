import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from scripts.crossbones_ram_demo import run


class CrossbonesRamDemoTests(TestCase):
    def test_audited_example_preserves_limitations_and_output(self):
        with TemporaryDirectory() as directory, patch('scripts.crossbones_ram_demo.source_commit', return_value='test'):
            output = Path(directory) / 'example.json'
            run(output)
            data = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(data['audit_issues'], [])
            self.assertEqual(data['stop_on_attacker'], 'Blacklight')
            self.assertIn('Weapons Blazing', data['crossbones_subset']['omitted_powers'])
            missed = {e['trigger'] for e in data['result']['log'] if e['type'] == 'ram_attack'
                      and not e['transaction']['parameters']['success']}
            self.assertTrue(any(e['type'] == 'parry_start' and e['source_trigger'] in missed
                                for e in data['result']['log']))
            original = output.read_bytes()
            with self.assertRaises((FileExistsError, ValueError)):
                run(output)
            self.assertEqual(output.read_bytes(), original)
