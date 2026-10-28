"""Real temporary Git repositories prove immutable result/source binding."""

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.freeze_results import freeze
from scripts.verify_sources import (INDEX_NAME, HISTORICAL_NAME, HISTORICAL_SCHEMA, LEGACY_COPY_NOTE,
                                    LEGACY_SOURCE_ALIASES, load_index, relative_source,
                                    snapshot_source_hash, verify, verify_result)


class TestResultSnapshots(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='blacklight-provenance-')
        self.temporary_root = Path(self.temporary.name).resolve()
        self.root = self.temporary_root / 'repo'
        self.root.mkdir()
        (self.root / 'results').mkdir()
        self.git('init', '--quiet')
        self.source = self.root / 'source.py'
        self.source.write_bytes(b'# source v1\n')
        self.git('add', 'source.py')
        self.git('commit', '--quiet', '-m', 'source v1')
        self.base = self.git('rev-parse', 'HEAD').strip()
        self.result = self.write_result('example.json')

    def tearDown(self):
        expected_parent = Path(tempfile.gettempdir()).resolve()
        if (not self.temporary_root.is_relative_to(expected_parent)
                or not self.temporary_root.name.startswith('blacklight-provenance-')):
            raise AssertionError('Unexpected temporary fixture cleanup path')
        self.temporary.cleanup()

    def git(self, *args):
        result = subprocess.run(
            ['git', '-c', 'user.name=Snapshot Test', '-c', 'user.email=test@localhost',
             '-c', 'core.autocrlf=false', *args], cwd=self.root,
            check=True, capture_output=True, text=True)
        return result.stdout

    def write_result(self, name, sources=None):
        payload = {'damage_model': 'literal_marvel_pool_v2',
                   'source_sha256': sources if sources is not None else {
                       'source.py': sha256(self.source.read_bytes()).hexdigest()},
                   'outcomes': {'win': 1, 'loss': 0}}
        path = self.root / 'results' / name
        path.write_text(json.dumps(payload), encoding='utf-8', newline='\n')
        return path

    def test_freeze_binds_exact_data_and_immutable_source_commit(self):
        index = freeze(self.base, root=self.root)
        record = index['results']['example.json']
        self.assertEqual(record['source_commit'], self.base)
        self.assertEqual(record['result_sha256'], sha256(self.result.read_bytes()).hexdigest())
        mode, issues = verify_result(self.result, root=self.root)
        self.assertEqual(issues, [])
        self.assertEqual(mode, 'live+snapshot:' + self.base)

    def test_source_evolution_preserves_old_proof_and_live_only_reports_drift(self):
        freeze(self.base, root=self.root)
        self.source.write_bytes(b'# a later source\n')
        mode, issues = verify_result(self.result, root=self.root)
        self.assertEqual((mode, issues), ('snapshot:' + self.base, []))
        _, live_issues = verify_result(self.result, root=self.root, live_only=True)
        self.assertTrue(any('SHA-256 mismatch' in issue for issue in live_issues))

    def test_tampered_result_bytes_fail_even_with_unchanged_source(self):
        freeze(self.base, root=self.root)
        payload = json.loads(self.result.read_text())
        payload['outcomes']['win'] = 100
        self.result.write_text(json.dumps(payload), encoding='utf-8')
        _, issues = verify_result(self.result, root=self.root)
        self.assertTrue(any('result bytes differ' in issue for issue in issues))

    def test_wrong_snapshot_cannot_hide_behind_matching_live_files(self):
        freeze(self.base, root=self.root)
        self.source.write_bytes(b'# source v2\n')
        self.git('commit', '--quiet', '-am', 'source v2')
        wrong = self.git('rev-parse', 'HEAD').strip()
        self.source.write_bytes(b'# source v1\n')  # Live bytes match the old result.
        index_path = self.root / 'results' / INDEX_NAME
        index = json.loads(index_path.read_text())
        index['results']['example.json']['source_commit'] = wrong
        index_path.write_text(json.dumps(index), encoding='utf-8')
        _, issues = verify_result(self.result, root=self.root)
        self.assertTrue(any('declared source commit' in issue for issue in issues))

    def test_uncommitted_source_cannot_be_frozen_as_old_commit(self):
        self.source.write_bytes(b'# uncommitted code\n')
        self.write_result('example.json')
        with self.assertRaisesRegex(ValueError, 'does not match committed source'):
            freeze(self.base, root=self.root)
        self.assertFalse((self.root / 'results' / INDEX_NAME).exists())

    def test_freezing_new_version_preserves_unchanged_old_records(self):
        freeze(self.base, root=self.root)
        self.source.write_bytes(b'# source v2\n')
        self.git('commit', '--quiet', '-am', 'source v2')
        newer = self.git('rev-parse', 'HEAD').strip()
        second = self.write_result('newer.json')
        index = freeze(newer, root=self.root)['results']
        self.assertEqual(index['example.json']['source_commit'], self.base)
        self.assertEqual(index['newer.json']['source_commit'], newer)
        self.assertEqual(verify_result(self.result, root=self.root)[1], [])
        self.assertEqual(verify_result(second, root=self.root)[1], [])

    def test_mutable_branch_in_snapshot_index_is_rejected(self):
        freeze(self.base, root=self.root)
        path = self.root / 'results' / INDEX_NAME
        index = json.loads(path.read_text())
        index['results']['example.json']['source_commit'] = 'HEAD'
        path.write_text(json.dumps(index), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Malformed source-snapshot record'):
            load_index(self.root)

    def test_external_source_must_be_preserved_in_repository_before_freezing(self):
        external = self.temporary_root / 'external.py'
        external.write_bytes(b'# outside the Git root\n')
        self.write_result('example.json', {str(external): sha256(external.read_bytes()).hexdigest()})
        with self.assertRaisesRegex(ValueError, 'outside the repository'):
            freeze(self.base, root=self.root)
        self.assertFalse((self.root / 'results' / INDEX_NAME).exists())

    def test_windows_relative_manifest_resolves_to_portable_git_path(self):
        nested = self.root / 'nested' / 'source.py'
        nested.parent.mkdir()
        nested.write_bytes(b'# historical nested source\n')
        self.git('add', 'nested/source.py')
        self.git('commit', '--quiet', '-m', 'nested source')
        commit = self.git('rev-parse', 'HEAD').strip()
        windows_name = r'nested\source.py'
        digest = sha256(nested.read_bytes()).hexdigest()
        self.assertEqual(relative_source(self.root, windows_name), 'nested/source.py')
        self.write_result('example.json', {windows_name: digest})
        freeze(commit, root=self.root)
        self.assertEqual(verify_result(self.result, root=self.root)[1], [])

    def test_exact_legacy_absolute_alias_works_after_repository_moves(self):
        old_name, relative = next(iter(LEGACY_SOURCE_ALIASES.items()))
        relocated = self.root / relative
        relocated.parent.mkdir(parents=True)
        relocated.write_bytes(b'# relocated known source\n')
        self.git('add', relative)
        self.git('commit', '--quiet', '-m', 'relocated source')
        commit = self.git('rev-parse', 'HEAD').strip()
        self.assertEqual(relative_source(self.root, old_name), relative)
        self.write_result('example.json', {old_name: sha256(relocated.read_bytes()).hexdigest()})
        freeze(commit, root=self.root)
        self.assertEqual(verify_result(self.result, root=self.root)[1], [])

    def test_unrelated_windows_absolute_source_is_not_guessed(self):
        with self.assertRaises(ValueError):
            relative_source(self.root, r'C:\unrelated\source.py')

    def test_missing_or_malformed_manifest_is_not_a_successful_freeze(self):
        for sources in ({}, {'source.py': None}, {'source.py': 'not-a-hash'}):
            self.write_result('example.json', sources)
            with self.assertRaises(ValueError):
                freeze(self.base, root=self.root)
            self.assertFalse((self.root / 'results' / INDEX_NAME).exists())

    def test_git_directory_is_not_treated_as_a_source_blob(self):
        self.assertIsNone(snapshot_source_hash(self.root, self.base, '.'))

    def test_freeze_refuses_replacement_of_existing_frozen_filename(self):
        freeze(self.base, root=self.root)
        index_path = self.root / 'results' / INDEX_NAME
        before = index_path.read_bytes()
        self.source.write_bytes(b'# source v2\n')
        self.git('commit', '--quiet', '-am', 'source v2')
        newer = self.git('rev-parse', 'HEAD').strip()
        self.write_result('example.json')
        with self.assertRaisesRegex(ValueError, 'result bytes differ'):
            freeze(newer, root=self.root)
        self.assertEqual(index_path.read_bytes(), before)

    def test_missing_registered_result_is_reported_and_cannot_be_refrozen(self):
        freeze(self.base, root=self.root)
        self.result.unlink()
        checked, issues = verify(root=self.root)
        self.assertEqual(checked, 0)
        self.assertTrue(any('frozen result is missing' in issue for issue in issues))
        with self.assertRaisesRegex(ValueError, 'frozen result is missing'):
            freeze(self.base, root=self.root)

    def test_tree_identity_cannot_impersonate_commit_even_with_same_sources(self):
        tree = self.git('rev-parse', 'HEAD^{tree}').strip()
        with self.assertRaisesRegex(ValueError, 'Git commit hashes'):
            snapshot_source_hash(self.root, tree, 'source.py')
        freeze(self.base, root=self.root)
        path = self.root / 'results' / INDEX_NAME
        index = json.loads(path.read_text())
        index['results']['example.json']['source_commit'] = tree
        path.write_text(json.dumps(index), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Malformed source-snapshot record'):
            verify(root=self.root)

    def test_new_malformed_results_cannot_disappear_by_filtering(self):
        payloads = ({'damage_model': 'literal_marvel_pool_v2'},
                    {'source_sha256': {'source.py': sha256(self.source.read_bytes()).hexdigest()}},
                    {'damage_model': 'mistyped_model', 'source_sha256': {
                        'source.py': sha256(self.source.read_bytes()).hexdigest()}},
                    [])
        for name in ('new.json', 'invalid_example.json', 'new_pre_mistake.json'):
            for payload in payloads:
                candidate = self.root / 'results' / name
                candidate.write_text(json.dumps(payload), encoding='utf-8')
                with self.assertRaises(ValueError):
                    verify(root=self.root)
                with self.assertRaises(ValueError):
                    freeze(self.base, root=self.root)
            candidate.unlink()

    def historical_exception(self, path):
        inventory = {'schema': HISTORICAL_SCHEMA, 'files': {
            path.name: {'sha256': sha256(path.read_bytes()).hexdigest(),
                        'reason': 'Historical fixture, preserved separately'}}}
        (self.root / 'results' / HISTORICAL_NAME).write_text(
            json.dumps(inventory), encoding='utf-8')

    def test_explicit_historical_inventory_is_checked_even_when_excluded(self):
        historical = self.root / 'results' / 'old.json'
        historical.write_bytes(b'{"historical": true}')
        self.historical_exception(historical)
        self.assertEqual(verify(root=self.root, allow_unfrozen=True), (1, []))
        freeze(self.base, root=self.root)
        historical.write_bytes(b'{"historical": false}')
        with self.assertRaisesRegex(ValueError, 'historical bytes differ'):
            verify(root=self.root)

    def test_inventory_claimed_legacy_copy_is_checked_independently(self):
        historical = self.root / 'results' / 'old.json'
        historical.write_bytes(b'{"historical": true}')
        legacy = self.root / 'results' / 'legacy_scalar_v1' / historical.name
        legacy.parent.mkdir()
        legacy.write_bytes(historical.read_bytes())
        inventory = {'schema': HISTORICAL_SCHEMA, 'files': {
            historical.name: {'sha256': sha256(historical.read_bytes()).hexdigest(),
                              'reason': LEGACY_COPY_NOTE}}}
        (self.root / 'results' / HISTORICAL_NAME).write_text(json.dumps(inventory), encoding='utf-8')
        self.assertEqual(verify(root=self.root, allow_unfrozen=True), (1, []))
        legacy.write_bytes(b'{"historical": false}')
        with self.assertRaisesRegex(ValueError, 'legacy copy'):
            verify(root=self.root, allow_unfrozen=True)

    def test_historical_exclusion_cannot_hide_frozen_result(self):
        freeze(self.base, root=self.root)
        self.historical_exception(self.result)
        _, issues = verify(root=self.root)
        self.assertTrue(any('cannot be historical exclusions' in issue for issue in issues))
        with self.assertRaisesRegex(ValueError, 'cannot be historical exclusions'):
            freeze(self.base, root=self.root)

    def test_unfrozen_result_requires_explicit_preparation_mode(self):
        checked, issues = verify(root=self.root)
        self.assertEqual(checked, 1)
        self.assertTrue(any('no frozen source record' in issue for issue in issues))
        self.assertEqual(verify(root=self.root, allow_unfrozen=True), (1, []))
        freeze(self.base, root=self.root)
        (self.root / 'results' / INDEX_NAME).unlink()
        self.assertTrue(verify(root=self.root)[1])

    def test_git_replace_cannot_rewrite_snapshot_sources(self):
        old_digest = sha256(self.source.read_bytes()).hexdigest()
        self.source.write_bytes(b'# source v2\n')
        self.git('commit', '--quiet', '-am', 'source v2')
        newer = self.git('rev-parse', 'HEAD').strip()
        self.git('replace', self.base, newer)
        self.assertEqual(snapshot_source_hash(self.root, self.base, 'source.py'), old_digest)
        self.write_result('example.json')
        with self.assertRaisesRegex(ValueError, 'does not match committed source'):
            freeze(self.base, root=self.root)
        self.assertFalse((self.root / 'results' / INDEX_NAME).exists())

    def test_failed_index_publication_preserves_previous_bytes(self):
        freeze(self.base, root=self.root)
        index_path = self.root / 'results' / INDEX_NAME
        before = index_path.read_bytes()
        self.write_result('new.json')
        for target in ('scripts.freeze_results.os.fsync', 'scripts.freeze_results.os.replace'):
            with patch(target, side_effect=OSError('injected publication failure')):
                with self.assertRaisesRegex(OSError, 'publication failure'):
                    freeze(self.base, root=self.root)
            self.assertEqual(index_path.read_bytes(), before)
            self.assertEqual(list(index_path.parent.glob('.source-snapshots-*.tmp')), [])


if __name__ == '__main__':
    unittest.main()
