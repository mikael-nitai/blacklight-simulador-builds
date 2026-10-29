"""Replay fixed first/middle/last seeds of each grapple exploration cell."""

from argparse import ArgumentParser
from hashlib import sha256
import json
import platform
from pathlib import Path

from blacklight.results_io import require_new_output, write_new_text
from combatants.duel_adapter import compile_duel
from combatants.sheets import load_sheet
from experimental.crossbones_reactive_grapple_subset import build_crossbones_reactive_grapple_subset
from scripts.audit_grapple_strategy_explore import audit
from scripts.grapple_strategy_explore import EVIDENCE, ROOT, VICTOR, policies_for, simulate


def check_live_sources(data):
    for name, expected in data['source_sha256'].items():
        path = (ROOT / name).resolve()
        if (not path.is_relative_to(ROOT.resolve()) or not path.is_file()
                or sha256(path.read_bytes()).hexdigest() != expected):
            raise ValueError(f'Live source missing or differs from frozen source: {name}')


def replay(dataset, output):
    dataset, output = Path(dataset), Path(output)
    if output.resolve().is_relative_to((ROOT / 'results').resolve()):
        raise ValueError('Experimental replay must not enter the certified inventory')
    require_new_output(output)
    raw = dataset.read_bytes()
    data = json.loads(raw.decode('utf-8'))
    issues = audit(data)
    if issues:
        raise RuntimeError(f'Exploration audit failed: {issues}')
    if data['runtime'] != {'python_version': platform.python_version(),
                           'python_implementation': platform.python_implementation()}:
        raise ValueError('Replay requires the recorded Python implementation and version')
    check_live_sources(data)
    subset = build_crossbones_reactive_grapple_subset(json.loads(EVIDENCE.read_text(encoding='utf-8')),
                                                       accept_incomplete=True)
    profiles = (subset.profile, compile_duel(load_sheet(VICTOR)))
    n = data['n_per_cell']
    checked = []
    for cell in data['cells']:
        for index in sorted({0, n // 2, n - 1}):
            expected = dict(cell['records'][index])
            expected.pop('index')
            actual = simulate(profiles, policies_for(cell['strategy']), subset.ranged_weapon, expected['seed'],
                              inside_attack_trouble=cell['inside_attack_trouble'], trigger_mode=cell['trigger_mode'])
            if actual != expected:
                raise RuntimeError(f'Replay mismatch {cell["strategy"]}/{index}')
            checked.append({'strategy': cell['strategy'], 'inside_attack_trouble': cell['inside_attack_trouble'],
                'trigger_mode': cell['trigger_mode'], 'index': index, 'seed': expected['seed'],
                'status': expected['status']})
    check_live_sources(data)
    result = {'schema': 'blacklight-experimental-grapple-strategy-replay-v1',
              'dataset_sha256': sha256(raw).hexdigest(), 'source_commit': data['source_commit'],
              'sampling': 'first, middle and last index per cell; duplicates removed', 'checked': checked,
              'issues': [], 'limitations': ['sampled replay, not an independent full replay or confirmation']}
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
