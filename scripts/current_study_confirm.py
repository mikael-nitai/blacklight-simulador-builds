"""Run the preregistered confirmation of selected current-rule duel policies."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path

from blacklight.experiment import ROOT
from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.runner import run_batch
from scripts.current_study_dev import INPUTS, SCENARIOS, configurations, declared_sources, source_commit
from scripts.current_study_select import load_cells, select_candidates


MASTER_SEED = 827104292
N_PER_CELL = 10000
SELECTION = ROOT / 'experiments/current_duel_study/development_selection_v1.json'
SELECTION_SHA256 = '87fec028587c5c18ce4a7f55f4a45b3bc282f34241d18d9f4e55f00f23dc4529'
SPEC = ROOT / 'CURRENT_DUEL_CONFIRM_SPEC.md'
FINALISTS = ('hammer_fast_hammer', 'hammer_fast_blade')
POLICIES = ('bare', *FINALISTS)


def validated_selection():
    raw = SELECTION.read_bytes()
    if sha256(raw).hexdigest() != SELECTION_SHA256:
        raise ValueError('Frozen exploratory selection bytes changed')
    selected = json.loads(raw)
    counts, _, inputs, commit, _ = load_cells()
    if (selected.get('schema') != 'blacklight-current-duel-development-selection-v1'
            or selected.get('phase') != 'development' or selected.get('source_commit') != commit
            or tuple(selected.get('finalists', ())) != FINALISTS
            or select_candidates(counts) != FINALISTS or selected.get('win_counts') != counts
            or selected.get('control') != 'bare'
            or any(selected.get('input_sha256', {}).get(name) != digest for name, digest in inputs.items())):
        raise ValueError('Selection does not match frozen preregistered development results')
    for name, digest in selected['input_sha256'].items():
        if sha256((ROOT / name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'Selection input changed: {name}')
    return selected


def confirmation_sources(policies, board, input_bytes, selection):
    sources = declared_sources(policies, board, input_bytes)
    for name in selection['input_sha256']:
        sources[name] = sha256((ROOT / name).read_bytes()).hexdigest()
    for path in (SELECTION, SPEC, Path(__file__).resolve()):
        sources[path.relative_to(ROOT).as_posix()] = sha256(path.read_bytes()).hexdigest()
    return sources


def output_path(scenario, policy):
    return ROOT / 'results' / f'current_duel_confirm_v1_{scenario}_{policy}.json'


def execute_cell(scenario_id, policy_id, *, n=N_PER_CELL, output=None):
    if scenario_id not in SCENARIOS or policy_id not in POLICIES or type(n) is not int or n < 1:
        raise ValueError('Unknown confirmation cell or invalid count')
    path = output_path(scenario_id, policy_id) if output is None else Path(output)
    require_new_output(path)
    selection = validated_selection()
    input_bytes = tuple(path.read_bytes() for path in INPUTS)
    hero, policies, scenarios = configurations(input_bytes)
    opponent, opponent_policy, distance, board = scenarios[scenario_id]
    policy = policies[policy_id]
    sources = confirmation_sources((policy, opponent_policy), board, input_bytes, selection)
    commit = source_commit(sources)
    payload = run_batch(hero, opponent, policy, opponent_policy, n=n, master_seed=MASTER_SEED,
                        initial_distance=distance, max_rounds=30, audit_every=1,
                        battlefield=board, extended_metrics=True)
    now_bytes = tuple(input_path.read_bytes() for input_path in INPUTS)
    require_unchanged_sources(sources, confirmation_sources((policy, opponent_policy), board,
                                                            now_bytes, selection))
    if source_commit(sources) != commit:
        raise RuntimeError('Confirmation source commit changed during execution')
    payload['source_sha256'].update(sources)
    payload['study'] = {'phase': 'confirmation', 'scenario_id': scenario_id, 'policy_id': policy_id,
                        'spec': SPEC.relative_to(ROOT).as_posix(), 'source_commit': commit,
                        'selection_sha256': SELECTION_SHA256, 'pre_registered_n': N_PER_CELL,
                        'n_matches_preregistration': n == N_PER_CELL,
                        'interpretation': 'limited synthetic physical duels, separate development and holdout'}
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    return payload


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--scenario', choices=SCENARIOS)
    parser.add_argument('--policy', choices=POLICIES)
    args = parser.parse_args()
    if args.all:
        if args.scenario or args.policy:
            parser.error('Use --all or both --scenario and --policy')
        cells = tuple((scenario, policy) for scenario in SCENARIOS for policy in POLICIES)
    elif args.scenario and args.policy:
        cells = ((args.scenario, args.policy),)
    else:
        parser.error('Specify --all or both --scenario and --policy')
    for scenario, policy in cells:
        require_new_output(output_path(scenario, policy))
    for index, (scenario, policy) in enumerate(cells, 1):
        print(f'Confirmação {index}/{len(cells)}: {scenario}, {policy}', flush=True)
        execute_cell(scenario, policy)
    print('Confirmation cells finished; holdout remains unexecuted.', flush=True)


if __name__ == '__main__':
    main()
