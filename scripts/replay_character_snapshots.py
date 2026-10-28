"""Re-execute frozen character examples without replacing their historical data.

This is a migration check, not a new strategy experiment. Every event/metric of
five duels and every aggregate/seed of one batch must match before publication.
"""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path
from blacklight.results_io import write_new_text

from blacklight.policies import RulePolicy
from combatants.runner import run_batch, run_duel
from combatants.sheets import parse_sheet
from .verify_sources import ROOT, verify_result


CASES = ('dodge_demo', 'modular_heal_demo', 'rank4_batch', 'rank4_demo',
         'stance_demo', 'standard_shield_demo')


def replay(path: Path) -> dict:
    _, issues = verify_result(path)
    if issues:
        raise ValueError(f'{path.name}: {issues}')
    stored = json.loads(path.read_text(encoding='utf-8'))
    sheets = tuple(parse_sheet(data) for data in stored['sheets'])
    policies = tuple(RulePolicy(**data) for data in stored['policies'])
    options = {'initial_distance': stored['initial_distance'],
               'max_rounds': stored['max_rounds']}
    if 'result' in stored:
        result = run_duel(*sheets, *policies, seed=stored['seed'], **options)
        compared = ('result', 'hero_outcome', 'sheets', 'policies', 'seed',
                    'initial_distance', 'max_rounds')
    else:
        indices = [row['index'] for row in stored['audited_traces']]
        interval = indices[1] - indices[0] if len(indices) > 1 else stored['n']
        result = run_batch(*sheets, *policies, n=stored['n'],
                           master_seed=stored['master_seed'], audit_every=interval,
                           **options)
        compared = ('outcomes', 'rates', 'metrics_all_starts', 'audited_traces',
                    'cell_sha256', 'sheets', 'policies', 'n', 'master_seed',
                    'initial_distance', 'max_rounds')
    normalized = json.loads(json.dumps(result))
    for field in compared:
        if normalized[field] != stored[field]:
            raise AssertionError(f'{path.name}: migration changed {field}')
    result['migration_reference'] = {'path': path.relative_to(ROOT).as_posix(),
                                    'sha256': sha256(path.read_bytes()).hexdigest(),
                                    'compared_fields': list(compared)}
    for source in (path, Path(__file__).resolve()):
        result['source_sha256'][source.relative_to(ROOT).as_posix()] = sha256(source.read_bytes()).hexdigest()
    return result


def main() -> None:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output-prefix', default='character_replay_v3')
    args = parser.parse_args()
    if (not args.output_prefix or
            any(char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-'
                for char in args.output_prefix)):
        parser.error('Output prefix must contain only letters, digits, underscore or hyphen')
    outputs = {case: ROOT / 'results' / f'{args.output_prefix}_{case}.json' for case in CASES}
    if any(path.exists() for path in outputs.values()):
        parser.error('Output already exists; choose a new versioned prefix')
    # Finish all comparisons before publishing any example from this invocation.
    payloads = {case: replay(ROOT / 'results' / f'generic_sheet_{case}.json') for case in CASES}
    for case, payload in payloads.items():
        write_new_text(outputs[case], json.dumps(payload, ensure_ascii=False, indent=2), newline='\n')
        detail = payload.get('hero_outcome', payload.get('outcomes'))
        print(f'{case}: exact migration comparison passed; {detail}')


if __name__ == '__main__':
    main()
