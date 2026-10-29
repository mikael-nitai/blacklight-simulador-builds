"""Replay fixed first/middle/last observations from every experimental cell."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path

from blacklight.results_io import require_new_output, write_new_text
from combatants.duel_adapter import compile_duel
from combatants.sheets import load_sheet
from experimental.crossbones_subset import build_crossbones_stopping_subset
from scripts.audit_ram_crossbones_explore import audit
from scripts.ram_crossbones_explore import EVIDENCE, VICTOR, ROOT, policies_for, simulate


def sample_indices(n):
    if type(n) is not int or n < 1:
        raise ValueError('A positive sample size is required')
    return tuple(sorted({0, n // 2, n - 1}))


def check_live_sources(data):
    for name, expected in data['source_sha256'].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
            raise ValueError(f'Source is missing or outside the project: {name}')
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Live source differs from frozen version: {name}')


def replay(dataset, output):
    dataset, output = Path(dataset), Path(output)
    if output.resolve().is_relative_to((ROOT / 'results').resolve()):
        raise ValueError('Experimental replay must not enter the certified results inventory')
    require_new_output(output)
    raw = dataset.read_bytes()
    data = json.loads(raw.decode('utf-8'))
    issues = audit(data)
    if issues:
        raise RuntimeError(f'Exploration audit failed: {issues}')
    check_live_sources(data)
    evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
    subset = build_crossbones_stopping_subset(evidence, accept_incomplete=True)
    profiles = (subset.profile, compile_duel(load_sheet(VICTOR)))
    checked = []
    for cell in data['cells']:
        policies = policies_for(cell['scenario'], cell['strategy'], cell['use_ram'])
        for index in sample_indices(data['n_per_cell']):
            expected = dict(cell['records'][index])
            seed = expected.pop('seed')
            expected.pop('index')
            replayed = expected.pop('unresolved_replayed', None)
            actual = simulate(profiles, policies, subset.ranged_weapon, seed)
            actual.pop('seed')
            if actual != expected or replayed is not None and replayed is not True:
                raise RuntimeError(f'Replay mismatch: {cell["scenario"]}/{cell["strategy"]}/{index}')
            checked.append({'scenario': cell['scenario'], 'strategy': cell['strategy'],
                            'use_ram': cell['use_ram'], 'index': index, 'seed': seed,
                            'status': expected['status']})
    check_live_sources(data)
    result = {'schema': 'blacklight-experimental-ram-crossbones-replay-v1',
              'dataset_sha256': sha256(raw).hexdigest(), 'source_commit': data['source_commit'],
              'sampling': 'first, middle and last index per cell; duplicates removed',
              'checked': checked, 'issues': [],
              'limitations': ['sampled replay; not a replay of every completed duel',
                              'unresolved cases repeat the incomplete prefix rather than an outcome']}
    write_new_text(output, json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(f'{len(checked)} fixed observations replayed; source and accounting checks passed.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    replay(args.dataset, args.output)


if __name__ == '__main__':
    main()
