"""Existing artifacts must survive every exposed result-writing path."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch

from blacklight.experiment import execute
from blacklight.results_io import write_new_text
from scripts import (character_sheet, corridor_replay, current_corridor_demos,
                     focus_experiment, focus_replay, group_replay, pool_v2_confirm,
                     pool_v2_replay, replay, split_fast_demos)


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

    def test_sheet_cli_records_repository_inputs_as_portable_paths(self):
        output = self.directory / 'sheet-duel.json'
        hero = 'characters/victor_halle/rank3_2026-10-27_split_fast.json'
        opponent = 'characters/examples/synthetic_rank4_split_fast.json'
        proc = subprocess.run(
            [sys.executable, '-B', '-m', 'scripts.character_sheet', 'duel',
             '--hero', hero, '--opponent', opponent, '--seed', '51', '--output', str(output)],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        sources = json.loads(output.read_text(encoding='utf-8'))['source_sha256']
        self.assertIn(hero, sources)
        self.assertIn(opponent, sources)
        self.assertTrue(all('\\' not in name for name in sources))

    def test_sheet_change_during_run_cannot_publish_a_misidentified_result(self):
        hero = self.directory / 'hero.json'
        opponent = self.directory / 'opponent.json'
        hero.write_bytes((ROOT / 'characters/victor_halle/rank3_2026-10-27_split_fast.json').read_bytes())
        opponent.write_bytes((ROOT / 'characters/examples/synthetic_rank4_split_fast.json').read_bytes())
        output = self.directory / 'duel.json'

        def change_sheet(*args, **kwargs):
            hero.write_bytes(hero.read_bytes() + b'\n')
            return {'source_sha256': {}, 'hero_outcome': 'win', 'result': {'winner': 'fixture'}}

        argv = ['character_sheet', 'duel', '--hero', str(hero), '--opponent', str(opponent),
                '--seed', '1', '--output', str(output)]
        with patch.object(sys, 'argv', argv), patch('scripts.character_sheet.run_duel', side_effect=change_sheet):
            with self.assertRaisesRegex(RuntimeError, 'sources changed'):
                character_sheet.main()
        self.assertFalse(output.exists())

    def test_demonstrations_abort_when_a_sheet_changes_during_the_batch(self):
        real_read = Path.read_bytes
        for module in (split_fast_demos, current_corridor_demos):
            prefix = 'foundation-test-no-output-' + module.__name__.split('.')[-1]
            reads = 0

            def altered_read(path):
                nonlocal reads
                data = real_read(path)
                if path == module.HERO:
                    reads += 1
                    return data if reads == 1 else data + b'\n'
                return data

            duel = {'source_sha256': {}, 'result': {'log': [{'type': 'fast_use_start'}]}}
            batch = {'source_sha256': {}, 'n': 1000, 'audited_traces': []}
            argv = [module.__name__, '--output-prefix', prefix]
            with self.subTest(module=module.__name__), \
                    patch.object(sys, 'argv', argv), patch.object(Path, 'read_bytes', altered_read), \
                    patch.object(module, 'run_duel', return_value=deepcopy(duel)), \
                    patch.object(module, 'run_batch', return_value=deepcopy(batch)):
                with self.assertRaisesRegex(RuntimeError, 'sources changed'):
                    module.main()
            self.assertFalse(any((ROOT / 'results').glob(prefix + '*.json')))

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

    def test_changed_sources_abort_long_experiments_before_writing(self):
        for label, run in (
            ('duel', lambda path: execute('smoke', 1, path)),
            ('confirm', lambda path: pool_v2_confirm.execute('confirm_v2', 1, path)),
        ):
            output = self.directory / f'{label}.json'
            target = ('blacklight.experiment.source_hashes' if label == 'duel'
                      else 'scripts.pool_v2_confirm.execution_sources')
            worker = ('blacklight.experiment.run_cell' if label == 'duel'
                      else 'scripts.pool_v2_confirm.run_cell')
            with self.subTest(label=label), \
                    patch(target, side_effect=[{'source': 'before'}, {'source': 'after'}]), \
                    patch(worker, return_value={'outcomes': {'win': 0}}), \
                    redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, 'sources changed'):
                    run(output)
            self.assertFalse(output.exists())

        output = self.directory / 'focus.json'
        with patch('scripts.focus_experiment.hashes',
                   side_effect=[{'source': 'before'}, {'source': 'after'}]), \
                patch('scripts.focus_experiment.run_cell',
                      return_value={'outcomes': {}, 'ever_demoralized': 0}), \
                patch.object(sys, 'argv', ['focus_experiment', '--stage', 'dev', '--output', str(output)]), \
                redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'sources changed'):
                focus_experiment.main()
        self.assertFalse(output.exists())

    def test_changed_sources_abort_each_replay_before_writing(self):
        operations = (
            (replay, lambda path: replay.replay('demo', 'mirror_hammer', 'hammer', 0, path)),
            (pool_v2_replay, lambda path: pool_v2_replay.replay('confirm_v2', 'mirror_hammer', 'hammer', 0, path)),
            (group_replay, lambda path: group_replay.replay(
                'description', group_replay.scenarios()[0][0], group_replay.POLICIES[0].name, 0, path)),
            (focus_replay, lambda path: focus_replay.replay(
                'description', 'M3', 'F0', focus_replay.STRATEGIES[0], 0, path)),
            (corridor_replay, lambda path: corridor_replay.replay(
                'description', 12, corridor_replay.gunners()[0][0], corridor_replay.POLICIES[0].name, 0, path)),
        )
        for index, (module, run) in enumerate(operations):
            output = self.directory / f'replay-{index}.json'
            with self.subTest(module=module.__name__), \
                    patch.object(module, 'execution_sources',
                                 side_effect=[{'source': 'before'}, {'source': 'after'}]):
                with self.assertRaisesRegex(RuntimeError, 'sources changed'):
                    run(output)
            self.assertFalse(output.exists())

    def test_small_real_legacy_experiment_writes_labeled_new_result(self):
        output = self.directory / 'smoke.json'
        with redirect_stdout(io.StringIO()):
            payload = execute('smoke', 1, output)
        self.assertEqual(payload['table_ruleset'], 'literal_marvel_pool_v2')
        self.assertEqual(json.loads(output.read_text(encoding='utf-8'))['source_sha256'],
                         payload['source_sha256'])
        self.assertTrue(all(row['metrics_all_starts']['rounds']['mc_se'] is None
                            for row in payload['rows']))

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
