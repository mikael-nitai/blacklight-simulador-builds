"""Analyze the preregistered confirmation after verifying its frozen inputs."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.batch_audit import audit_batch_metadata
from blacklight.experiment import conservative_win_difference, independent_win_difference, wilson
from blacklight.mechanics_contract import recorded_contract_status
from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.runner import _policy_types
from combatants.sheets import sheet_record
from scripts.current_study_confirm import (AMENDMENT, FINALISTS, MASTER_SEED, N_PER_CELL,
                                           POLICIES, SELECTION, SELECTION_SHA256, SPEC,
                                           output_path, validated_selection)
from scripts.current_study_dev import INPUTS, SCENARIOS, configurations, source_commit
from scripts.verify_sources import ROOT, load_index, verify_result

ALPHA = 0.05 / 15
PAIRS = ((FINALISTS[0], 'bare'), (FINALISTS[1], 'bare'),
         (FINALISTS[0], 'hammer'), (FINALISTS[1], 'hammer'), FINALISTS)


def compare(first, second):
    """Report both intervals; conclusions use the conservative interval only."""
    delta, low, high = conservative_win_difference(first, second, alpha=ALPHA)
    _, approx_low, approx_high = independent_win_difference(first, second, alpha=ALPHA)
    conclusion = 'first_higher' if low > 0 else 'second_higher' if high < 0 else 'inconclusive'
    return {'difference': delta, 'conservative_interval': [low, high],
            'newcombe_wilson_interval': [approx_low, approx_high], 'conclusion': conclusion}


def load_confirmation():
    selection = validated_selection()
    index = load_index(ROOT)
    hero, policies, scenarios = configurations(tuple(path.read_bytes() for path in INPUTS))
    commits, inputs, cells, seen_seeds = set(), {}, {}, set()
    development_seeds = set()
    for name in selection['input_sha256']:
        if name.startswith('results/current_duel_dev_v1_'):
            development = json.loads((ROOT / name).read_text(encoding='utf-8'))
            development_seeds.update(trace['seed'] for trace in development['audited_traces'])
    if len(development_seeds) != 15000:
        raise ValueError('Invalid development seed inventory')
    for scenario in SCENARIOS:
        cells[scenario] = {}
        opponent, opponent_policy, distance, board = scenarios[scenario]
        for name in POLICIES:
            path = output_path(scenario, name)
            _, issues = verify_result(path, root=ROOT, index=index)
            if issues:
                raise ValueError(f'{path.name}: {issues}')
            raw = path.read_bytes()
            digest = sha256(raw).hexdigest()
            if digest != index[path.name]['result_sha256']:
                raise ValueError(f'{path.name}: bytes changed during verification')
            record = json.loads(raw)
            study = record.get('study', {})
            if (record.get('schema') != 'blacklight-generic-character-batch-v1'
                    or record.get('table_ruleset') != 'split_fast_v3'
                    or record.get('n') != N_PER_CELL or record.get('master_seed') != MASTER_SEED
                    or record.get('max_rounds') != 30
                    or record.get('initial_distance') != (board.distance if board else distance)
                    or record.get('battlefield') != (board.record() if board else None)
                    or record.get('sheets') != [sheet_record(hero), sheet_record(opponent)]
                    or record.get('policies') != [asdict(policies[name]), asdict(opponent_policy)]
                    or record.get('policy_types') != _policy_types((policies[name], opponent_policy))
                    or study.get('phase') != 'confirmation' or study.get('scenario_id') != scenario
                    or study.get('policy_id') != name or study.get('pre_registered_n') != N_PER_CELL
                    or study.get('n_matches_preregistration') is not True
                    or study.get('source_commit') != index[path.name]['source_commit']
                    or study.get('selection_sha256') != SELECTION_SHA256
                    or study.get('seed_preflight') != {'development': 15000, 'confirmation': 120000, 'collisions': 0}
                    or record.get('source_sha256', {}).get(SPEC.relative_to(ROOT).as_posix()) != sha256(SPEC.read_bytes()).hexdigest()
                    or record.get('source_sha256', {}).get(AMENDMENT.relative_to(ROOT).as_posix()) != sha256(AMENDMENT.read_bytes()).hexdigest()
                    or recorded_contract_status(record) != 'recorded_verified'
                    or record.get('extended_metrics_schema') != 'blacklight-batch-combat-samples-v1'):
                raise ValueError(f'{path.name}: preregistered configuration mismatch')
            issues = audit_batch_metadata(record)
            if issues:
                raise ValueError(f'{path.name}: batch audit failed: {issues}')
            for trace in record['audited_traces']:
                seed = trace['seed']
                if seed in seen_seeds or seed in development_seeds:
                    raise ValueError('Duplicate or overlapping recorded seed')
                seen_seeds.add(seed)
            commits.add(study['source_commit'])
            inputs[path.relative_to(ROOT).as_posix()] = digest
            wins = record['outcomes']['win']
            cells[scenario][name] = {'n': N_PER_CELL, 'win_rate': wins / N_PER_CELL,
                                     'outcomes': record['outcomes'],
                                     'wilson_95': list(wilson(wins, N_PER_CELL)),
                                     'metrics_all_starts': record['extended_metrics_all_starts']}
    if len(commits) != 1 or len(seen_seeds) != 120000:
        raise ValueError('Confirmation commits or seed inventory are inconsistent')
    return cells, inputs, next(iter(commits))


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to((ROOT / 'results').resolve()):
        parser.error('Analysis belongs outside the frozen batch results directory')
    require_new_output(args.output)
    script = Path(__file__).resolve()
    script_hash = {script.relative_to(ROOT).as_posix(): sha256(script.read_bytes()).hexdigest()}
    analysis_commit = source_commit(script_hash)
    cells, inputs, commit = load_confirmation()
    comparisons = {scenario: [{'first': a, 'second': b, **compare(cells[scenario][a], cells[scenario][b])}
                              for a, b in PAIRS] for scenario in SCENARIOS}
    references = (SELECTION, SPEC, AMENDMENT, script)
    before = {**inputs, **{p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest()
                           for p in references}}
    after = {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in before}
    require_unchanged_sources(before, after)
    if source_commit(script_hash) != analysis_commit:
        raise RuntimeError('Analysis source commit changed during execution')
    payload = {'schema': 'blacklight-current-duel-confirmation-analysis-v1',
               'source_commit': commit, 'analysis_commit': analysis_commit,
               'n_per_cell': N_PER_CELL, 'alpha_per_comparison': ALPHA,
               'input_sha256': before, 'cells': cells, 'comparisons': comparisons,
               'limitations': ['synthetic physical duels; not representative of all encounters',
                               'coverage assumes independent Bernoulli starts',
                               'individual Wilson intervals are descriptive, not simultaneous',
                               'holdout has not been analyzed']}
    write_new_text(args.output, json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print('Confirmation analysis recorded; holdout remains unexecuted.')


if __name__ == '__main__':
    main()
