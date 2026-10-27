"""Bind completed result bytes to immutable, verified source commits."""

from argparse import ArgumentParser
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile

from .verify_sources import (ROOT, INDEX_NAME, INDEX_SCHEMA, eligible_results,
                             git_commit, load_index, snapshot_source_hash, source_manifest,
                             verify_result, verify)


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
