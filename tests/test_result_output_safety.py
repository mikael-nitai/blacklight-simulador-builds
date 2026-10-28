"""Existing artifacts must survive every exposed result-writing path."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest

from blacklight.experiment import execute
from blacklight.results_io import write_new_text
from scripts import (character_sheet, corridor_replay, focus_replay, group_replay,
                     pool_v2_confirm, pool_v2_replay, replay)


ROOT = Path(__file__).resolve().parents[1]


class TestResultOutputSafety(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='blacklight-output-')
        self.directory = Path(self.temporary.name).resolve()

    def tearDown(self):
        if (not self.directory.is_relative_to(Path(tempfile.gettempdir()).resolve())
                or not self.directory.name.startswith('blacklight-output-')):
            raise AssertionError('Unexpected temporary fixture cleanup path')
        self.temporary.cleanup()

    def test_existing_files_survive_replay_and_programmatic_entry_points(self):
        output = self.directory / 'result.json'
        original = b'original historical bytes\n'
        output.write_bytes(original)
        operations = (
            lambda: replay.replay('demo', 'mirror_hammer', 'hammer', 0, output),
            lambda: pool_v2_replay.replay('confirm_v2', 'mirror_hammer', 'hammer', 0, output),
            lambda: group_replay.replay('description', 'G1', 'anything', 0, output),
            lambda: focus_replay.replay('description', 'M3', 'F0', 'anything', 0, output),
            lambda: corridor_replay.replay('description', 12, 'anything', 'anything', 0, output),
            lambda: character_sheet.write_json(output, {'changed': True}),
            lambda: execute('smoke', 1, output),
            lambda: pool_v2_confirm.execute('confirm_v2', 1, output),
        )
        for operation in operations:
            with self.subTest(operation=operation):
                with self.assertRaises(FileExistsError):
                    operation()
                self.assertEqual(output.read_bytes(), original)

    def test_real_replay_creates_new_file_and_refuses_second_write(self):
        output = self.directory / 'new.json'
        data = replay.replay('demo', 'mirror_hammer', 'hammer', 0, output)
        saved = output.read_bytes()
        self.assertEqual(json.loads(saved)['seed'], data['seed'])
        self.assertEqual(json.loads(saved)['table_ruleset'], 'literal_marvel_pool_v2')
        with self.assertRaises(FileExistsError):
            replay.replay('demo', 'mirror_hammer', 'hammer', 0, output)
        self.assertEqual(output.read_bytes(), saved)

    def test_competing_creators_cannot_replace_each_others_output(self):
        output = self.directory / 'race.txt'
        ready = Barrier(2)

        def create(content):
            ready.wait()
            try:
                write_new_text(output, content)
                return 'created'
            except FileExistsError:
                return 'exists'

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(create, ('first', 'second')))
        self.assertCountEqual(results, ['created', 'exists'])
        self.assertIn(output.read_text(encoding='utf-8'), ('first', 'second'))

    def test_legacy_fixed_output_commands_require_explicit_fresh_destination(self):
        output = self.directory / 'historic.json'
        original = b'historical sentinel'
        output.write_bytes(original)
        for module in ('blacklight.search', 'blacklight.sensitivity', 'scripts.holdout',
                       'scripts.secondary_metrics', 'scripts.adversarial_scenarios'):
            with self.subTest(module=module):
                proc = subprocess.run(
                    [sys.executable, '-B', '-m', module, '--historical-rules', '--output', str(output)],
                    cwd=ROOT, capture_output=True, text=True, timeout=10)
                self.assertNotEqual(proc.returncode, 0)
                self.assertIn('already exists', proc.stderr)
                self.assertEqual(output.read_bytes(), original)
                no_opt_in = subprocess.run(
                    [sys.executable, '-B', '-m', module, '--output', str(self.directory / 'new.json')],
                    cwd=ROOT, capture_output=True, text=True, timeout=10)
                self.assertNotEqual(no_opt_in.returncode, 0)
                self.assertIn('--historical-rules', no_opt_in.stderr)
                self.assertFalse((self.directory / 'new.json').exists())


if __name__ == '__main__':
    unittest.main()
