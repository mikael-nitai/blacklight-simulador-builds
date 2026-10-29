import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from scripts.double_tap_demo import run


class DoubleTapDemoTests(TestCase):
    def test_audited_demo_is_preserved_without_overwriting(self):
        with TemporaryDirectory() as directory, patch('scripts.double_tap_demo.source_commit', return_value='test'):
            output = Path(directory) / 'duel.json'
            run(output)
            payload = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(payload['audit_issues'], [])
            self.assertEqual(payload['seed'], 7)
            self.assertTrue(any(event['type'] == 'double_tap_end'
                                for event in payload['result']['log']))
            saved = output.read_bytes()
            with self.assertRaises((FileExistsError, ValueError)):
                run(output)
            self.assertEqual(output.read_bytes(), saved)
