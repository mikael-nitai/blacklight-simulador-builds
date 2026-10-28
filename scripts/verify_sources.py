"""Verify result bytes and sources against live files or an explicit Git snapshot."""

from argparse import ArgumentParser
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path, PureWindowsPath
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
INDEX_NAME = 'source_snapshots.json'
INDEX_SCHEMA = 'blacklight.source_snapshots.v1'
HISTORICAL_NAME = 'historical_inventory.json'
HISTORICAL_SCHEMA = 'blacklight.historical_inventory.v1'

# Exact aliases for the two repository-owned sheets written as absolute paths
# in three original Windows results. Their hashes are still checked against
# the recorded Git commit; unknown external paths are never remapped.
LEGACY_SOURCE_ALIASES = {
    r'C:\Users\avada\Documents\ChatGPT\Simulador Builds\characters\victor_halle\rank3_2026-10-26.json':
        'characters/victor_halle/rank3_2026-10-26.json',
    r'C:\Users\avada\Documents\ChatGPT\Simulador Builds\characters\examples\synthetic_rank4.json':
        'characters/examples/synthetic_rank4.json',
}


def _valid_name(name) -> bool:
    return isinstance(name, str) and bool(re.fullmatch(r'[A-Za-z0-9_.-]+\.json', name)) and name not in {INDEX_NAME, HISTORICAL_NAME}


@lru_cache(maxsize=128)
def _is_commit(root: str, identity: str) -> bool:
    result = subprocess.run(['git', '--no-replace-objects', 'cat-file', '-t', identity], cwd=root,
                            capture_output=True, text=True)
    return result.returncode == 0 and result.stdout.strip() == 'commit'


def git_commit(root: Path, ref: str) -> str:
    result = subprocess.run(
        ['git', '--no-replace-objects', 'rev-parse', '--verify', '--end-of-options', f'{ref}^{{commit}}'],
        cwd=root, check=True, capture_output=True, text=True)
    commit = result.stdout.strip()
    if not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', commit):
        raise ValueError('Git did not return an immutable commit identity')
    return commit


def source_path(root: Path, source: str) -> Path:
    """Resolve saved Windows-relative names on any host, without guessing aliases."""
    normalized = LEGACY_SOURCE_ALIASES.get(source, source)
    if PureWindowsPath(normalized).is_absolute() and not Path(normalized).is_absolute():
        raise ValueError(f'Windows absolute source cannot be located on this host: {source}')
    path = Path(normalized.replace('\\', '/'))
    if not path.is_absolute():
        path = root / path
    return path


def relative_source(root: Path, source: str) -> str:
    path = source_path(root, source)
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f'Source outside the repository cannot use its Git snapshot: {source}') from exc


@lru_cache(maxsize=2048)
def _git_hash(root: str, commit: str, relative: str) -> str | None:
    result = subprocess.run(['git', '--no-replace-objects', 'cat-file', 'blob', f'{commit}:{relative}'],
                            cwd=root, capture_output=True)
    return sha256(result.stdout).hexdigest() if result.returncode == 0 else None


def snapshot_source_hash(root: Path, commit: str, source: str) -> str | None:
    if (not isinstance(commit, str)
            or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', commit)
            or not _is_commit(str(root.resolve()), commit)):
        raise ValueError('Snapshot references must be full immutable Git commit hashes')
    return _git_hash(str(root.resolve()), commit, relative_source(root, source))


def load_index(root: Path = ROOT) -> dict:
    path = root / 'results' / INDEX_NAME
    if not path.is_file():
        return {}
    index = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(index, dict) or set(index) != {'schema', 'results'} or index['schema'] != INDEX_SCHEMA
            or not isinstance(index['results'], dict)):
        raise ValueError('Malformed source-snapshot index')
    for name, record in index['results'].items():
        if (not _valid_name(name)
                or not isinstance(record, dict)
                or set(record) != {'result_sha256', 'source_commit'}
                or not isinstance(record['result_sha256'], str)
                or not re.fullmatch(r'[0-9a-f]{64}', record['result_sha256'])
                or not isinstance(record['source_commit'], str)
                or not re.fullmatch(r'(?:[0-9a-f]{40}|[0-9a-f]{64})', record['source_commit'])
                or not _is_commit(str(root.resolve()), record['source_commit'])):
            raise ValueError(f'Malformed source-snapshot record: {name}')
    return index['results']


def historical_inventory(root: Path = ROOT) -> dict:
    """Explicit, byte-bound exceptions; a new malformed result is never guessed historical."""
    path = root / 'results' / HISTORICAL_NAME
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(payload, dict) or set(payload) != {'schema', 'files'}
            or payload['schema'] != HISTORICAL_SCHEMA or not isinstance(payload['files'], dict)):
        raise ValueError('Malformed historical inventory')
    for name, record in payload['files'].items():
        if (not _valid_name(name) or not isinstance(record, dict)
                or set(record) != {'sha256', 'reason'}
                or not isinstance(record['sha256'], str)
                or not re.fullmatch(r'[0-9a-f]{64}', record['sha256'])
                or not isinstance(record['reason'], str) or not record['reason'].strip()):
            raise ValueError(f'Malformed historical inventory entry: {name}')
        result = root / 'results' / name
        if not result.is_file() or sha256(result.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError(f'{name}: historical bytes differ from the explicit inventory')
    return payload['files']


def source_manifest(payload: dict) -> dict[str, str]:
    if not isinstance(payload, dict):
        raise ValueError('Result payload must be an object')
    sources = payload.get('source_sha256')
    if not isinstance(sources, dict) or not sources:
        raise ValueError('Missing source manifest')
    if any(not isinstance(name, str) or not name
           or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)
           for name, digest in sources.items()):
        raise ValueError('Malformed source hash entry')
    return sources


def eligible_results(root: Path = ROOT, *, include_historical: bool = False):
    excluded = historical_inventory(root)
    for path in sorted((root / 'results').glob('*.json')):
        if path.name in {INDEX_NAME, HISTORICAL_NAME}:
            continue
        if not include_historical and path.name in excluded:
            continue
        payload = json.loads(path.read_text(encoding='utf-8'))
        source_manifest(payload)
        if path.name not in excluded and payload.get('damage_model') != 'literal_marvel_pool_v2':
            raise ValueError(f'{path.name}: unknown damage model; declare or migrate this result explicitly')
        yield path, payload


def verify_result(path: Path, *, root: Path = ROOT, index: dict | None = None,
                  live_only: bool = False, allow_unfrozen: bool = False) -> tuple[str, list[str]]:
    records = load_index(root) if index is None else index
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        sources = source_manifest(payload)
    except (ValueError, OSError) as exc:
        return 'invalid', [f'{path.name}: {exc}']
    record = records.get(path.name)
    if record is None and not allow_unfrozen:
        return 'unfrozen', [f'{path.name}: result has no frozen source record']
    if record and sha256(path.read_bytes()).hexdigest() != record['result_sha256']:
        return 'invalid', [f'{path.name}: result bytes differ from the frozen record']
    issues = []
    used_snapshot = False
    for source, expected in sources.items():
        try:
            live = source_path(root, source)
        except ValueError as exc:
            issues.append(f'{path.name}: {exc}')
            continue
        actual = sha256(live.read_bytes()).hexdigest() if live.is_file() else None
        if record and not live_only:
            try:
                matched = snapshot_source_hash(root, record['source_commit'], source) == expected
            except ValueError:
                matched = False
            if not matched:
                issues.append(f'{path.name}: {source} does not match the declared source commit')
            used_snapshot |= actual != expected
        elif actual != expected:
            issues.append(f'{path.name}: {source} SHA-256 mismatch')
    mode = 'live'
    if record and not live_only:
        mode = ('snapshot:' if used_snapshot else 'live+snapshot:') + record['source_commit']
    return mode, issues


def verify(include_historical: bool = False, *, live_only: bool = False,
           root: Path = ROOT, allow_unfrozen: bool = False) -> tuple[int, list[str]]:
    records = load_index(root)
    checked = 0
    issues = []
    excluded = historical_inventory(root)
    overlap = records.keys() & excluded.keys()
    if overlap:
        issues.append(f'Frozen results cannot be historical exclusions: {sorted(overlap)}')
    for name in records:
        if not (root / 'results' / name).is_file():
            issues.append(f'{name}: frozen result is missing')
    for path, _ in eligible_results(root, include_historical=include_historical):
        checked += 1
        _, found = verify_result(path, root=root, index=records, live_only=live_only,
                                 allow_unfrozen=allow_unfrozen or path.name in excluded)
        issues.extend(found)
    return checked, issues


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--include-historical', action='store_true')
    parser.add_argument('--live-only', action='store_true')
    parser.add_argument('--allow-unfrozen', action='store_true',
                        help='Explicit preparation mode: also check new results against live sources')
    parser.add_argument('--details', action='store_true')
    args = parser.parse_args()
    try:
        checked, issues = verify(args.include_historical, live_only=args.live_only,
                                  allow_unfrozen=args.allow_unfrozen)
    except (ValueError, OSError) as exc:
        print(f'Verification failed: {exc}')
        raise SystemExit(1) from exc
    print(f'Checked {checked} result JSONs; {len(issues)} verification issues')
    if args.details:
        for path, _ in eligible_results(include_historical=args.include_historical):
            mode, _ = verify_result(path, live_only=args.live_only,
                                    allow_unfrozen=args.allow_unfrozen)
            print(f'{path.name}: {mode}')
    for issue in issues:
        print(issue)
    if issues:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
