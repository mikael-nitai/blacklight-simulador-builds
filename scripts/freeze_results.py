"""Bind completed result bytes to immutable, verified source commits."""

from argparse import ArgumentParser
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tempfile

from blacklight.mechanics_contract import recorded_contract_status
from blacklight.batch_audit import audit_batch_metadata
from blacklight.rulesets import SUPPORTED_RULESETS
from combatants.policy_provenance import recorded_builtin_policies
from .verify_sources import (ROOT, INDEX_NAME, INDEX_SCHEMA, eligible_results,
                             git_commit, load_index, relative_source, snapshot_source_hash, source_manifest,
                             verify_result, verify)


GENERIC_SCHEMAS = frozenset(('blacklight-generic-character-duel-v1',
                             'blacklight-generic-character-batch-v1'))
REQUIRED_CORE = frozenset(('blacklight/engine.py', 'blacklight/policies.py',
                           'blacklight/rulesets.py', 'blacklight/ruleset_audit.py',
                           'blacklight/audit.py', 'blacklight/mechanics_contract.py',
                           'combatants/runner.py',
                           'combatants/sheets.py', 'combatants/split_fast.py',
                           'combatants/terrain_policies.py', 'combatants/policy_provenance.py'))


def require_generic_provenance(payload: dict, root: Path, commit: str) -> None:
    """Do not freeze a new generic result with unknown policies or partial core sources."""
    if payload.get('schema') in ('blacklight-experimental-character-group-v1',
                                 'blacklight-experimental-character-group-v2'):
        raise ValueError('Experimental group output has no certified freezing contract')
    if payload.get('schema') not in GENERIC_SCHEMAS:
        return
    if (payload.get('policy_provenance') != 'project_builtin'
            or not recorded_builtin_policies(payload.get('policy_types'))):
        raise ValueError('Generic result has unverified policy provenance; keep it experimental')
    if (not isinstance(payload.get('table_ruleset'), str)
            or payload['table_ruleset'] not in SUPPORTED_RULESETS):
        raise ValueError('Generic result has an unsupported declared table ruleset')
    if (payload.get('schema') == 'blacklight-generic-character-duel-v1'
            and payload.get('audit_issues') != []):
        raise ValueError('Generic duel has a missing or failed recorded audit')
    if payload.get('schema') == 'blacklight-generic-character-batch-v1':
        issues = audit_batch_metadata(payload)
        if issues:
            raise ValueError(f'Generic batch audit is incomplete or inconsistent: {issues}')
    if recorded_contract_status(payload) != 'recorded_verified':
        raise ValueError('Generic result has missing or inconsistent mechanics contract provenance')
    result = subprocess.run(
        ['git', '--no-replace-objects', 'ls-tree', '-r', '--name-only', commit, '--',
         'blacklight', 'combatants'], cwd=root, check=True, capture_output=True, text=True)
    required = {name for name in result.stdout.splitlines() if name.endswith('.py')}
    if not REQUIRED_CORE <= required:
        raise ValueError('Generic result source commit lacks the required core provenance files')
    if payload.get('battlefield') is not None:
        required.update(('experimental/__init__.py', 'experimental/corridor.py',
                         'experimental/corridor_audit.py', 'CORRIDOR_SPEC.md', 'CURRENT_CORRIDOR.md'))
    recorded = {relative_source(root, name) for name in source_manifest(payload)}
    missing = required - recorded
    if missing:
        raise ValueError(f'Generic result has incomplete source provenance: {sorted(missing)}')


def freeze(ref: str, *, root: Path = ROOT) -> dict:
    commit = git_commit(root, ref)
    records = load_index(root)
    _, issues = verify(root=root, allow_unfrozen=True)
    if issues:
        raise ValueError(f'Cannot freeze an invalid result inventory: {issues}')
    updated = dict(records)
    for path, payload in eligible_results(root):
        digest = sha256(path.read_bytes()).hexdigest()
        previous = records.get(path.name)
        if previous:
            if previous['result_sha256'] != digest:
                raise ValueError(f'{path.name}: frozen result cannot be replaced; use a new versioned filename')
            _, issues = verify_result(path, root=root, index=records)
            if issues:
                raise ValueError(f'Existing frozen result failed verification: {issues}')
            continue
        require_generic_provenance(payload, root, commit)
        sources = source_manifest(payload)
        for source, expected in sources.items():
            if snapshot_source_hash(root, commit, source) != expected:
                raise ValueError(f'{path.name}: {source} does not match committed source {commit}')
        updated[path.name] = {'result_sha256': digest, 'source_commit': commit}
    index = {'schema': INDEX_SCHEMA, 'results': updated}
    output = root / 'results' / INDEX_NAME
    content = json.dumps(index, ensure_ascii=False, indent=2) + '\n'
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='\n',
                                         prefix='.source-snapshots-', suffix='.tmp',
                                         dir=output.parent, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, output)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return index


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--ref', default='HEAD')
    args = parser.parse_args()
    index = freeze(args.ref)
    print(f"Bound {len(index['results'])} results to verified immutable source snapshots")


if __name__ == '__main__':
    main()
