import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from scripts.ram_stop_demo import run


class RamStopDemoTests(TestCase):
    def test_audited_example_is_preserved_without_overwriting(self):
        with TemporaryDirectory() as directory, patch('scripts.ram_stop_demo.source_commit', return_value='test'):
            output = Path(directory) / 'example.json'
            run(output)
            data = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(data['audit_issues'], [])
            self.assertEqual(data['result']['final_health'], [-1, 210])
            self.assertTrue(any(event['type'] == 'ram_incapacity_stop' for event in data['result']['log']))
            original = output.read_bytes()
            with self.assertRaises((FileExistsError, ValueError)):
                run(output)
            self.assertEqual(output.read_bytes(), original)
