"""Read-only classification of frozen and inventoried historical results."""

from argparse import ArgumentParser
from collections import Counter
import json
from pathlib import Path

from combatants.duel_adapter import CURRENT_RULESET, LEGACY_RULESET
from .verify_sources import (ROOT, eligible_results, historical_inventory,
                             load_index, verify, verify_result)


# These exact snapshots precede commit 00f06f9, which introduced the current
# two-check Fast Strikes. Focus-only results may not exercise Fast at all.
PRE_SPLIT_FAST_COMMITS = frozenset({
    'f9c540a8c2cf9ffbb619dba5deda1d14bb06f50a',
    '7cdf0940303934231549cb383f7d656ca6a275b9',
})


def classify_ruleset(payload: dict, source_commit: str) -> str:
    declared = payload.get('table_ruleset')
    if declared == CURRENT_RULESET:
        return 'current_ruleset_declared'
    if declared == LEGACY_RULESET:
        return 'historical_ruleset_declared'
    if declared is None and source_commit in PRE_SPLIT_FAST_COMMITS:
        return 'historical_snapshot_pre_split_fast'
    return 'unknown_ruleset'


def zero_width_intervals(payload) -> int:
    """Count interval fields known to have been emitted by these experiments."""
    fields = {'simultaneous_ci_bonferroni', 'ci95_independent'}
    if isinstance(payload, dict):
        own = sum(1 for key, value in payload.items()
                  if key in fields and isinstance(value, list) and len(value) == 2
                  and all(type(item) in (int, float) for item in value)
                  and value[0] == value[1])
        return own + sum(zero_width_intervals(value) for value in payload.values())
    if isinstance(payload, list):
        return sum(zero_width_intervals(value) for value in payload)
    return 0


def inventory(root: Path = ROOT) -> dict:
    checked, issues = verify(root=root)
    if issues:
        raise ValueError(f'Cannot classify unverified results: {issues}')
    index = load_index(root)
    entries = []
    for path, payload in eligible_results(root):
        record = index[path.name]
        _, live_issues = verify_result(path, root=root, index=index, live_only=True)
        entries.append({
            'name': path.name,
            'classification': classify_ruleset(payload, record['source_commit']),
            'source_commit': record['source_commit'],
            'listed_sources': 'differ_from_live' if live_issues else 'match_live',
            'listed_source_differences': len(live_issues),
            'zero_width_intervals': zero_width_intervals(payload),
        })
    for name in sorted(historical_inventory(root)):
        payload = json.loads((root / 'results' / name).read_text(encoding='utf-8'))
        entries.append({'name': name, 'classification': 'historical_scalar_inventory',
                        'source_commit': None, 'listed_sources': 'not_frozen_in_index',
                        'listed_source_differences': None,
                        'zero_width_intervals': zero_width_intervals(payload)})
    return {
        'schema': 'blacklight.result-compatibility.v1',
        'frozen_results_checked': checked,
        'entries': entries,
        'limitations': [
            'Classification and source hashes do not validate RPG rules or statistical conclusions.',
            'Matching listed sources does not prove an exhaustive dependency manifest.',
            'Pre-split snapshots are historical; whether Fast affected a particular scenario requires inspection.',
            'Only root results and explicitly inventoried scalar copies are included.',
        ],
    }


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--details', action='store_true')
    args = parser.parse_args()
    try:
        report = inventory()
    except (ValueError, OSError) as exc:
        parser.exit(1, f'Cannot verify result inventory: {exc}\n')
    entries = report['entries']
    print(f"Frozen results checked: {report['frozen_results_checked']}")
    for category, count in sorted(Counter(row['classification'] for row in entries).items()):
        print(f'{category}: {count}')
    print('Zero-width historical intervals:', sum(row['zero_width_intervals'] for row in entries))
    print('Source matching does not by itself establish rule or conclusion validity.')
    if args.details:
        for row in entries:
            print(f"{row['name']}: {row['classification']}; {row['listed_sources']}; "
                  f"zero-width intervals={row['zero_width_intervals']}")


if __name__ == '__main__':
    main()
