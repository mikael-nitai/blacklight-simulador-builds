"""Select exploratory finalists using the fixed, precommitted study rule."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.batch_audit import audit_batch_metadata
from blacklight.mechanics_contract import recorded_contract_status
from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.runner import _policy_types
from combatants.sheets import sheet_record
from scripts.current_study_dev import (INPUTS, MASTER_SEED, N_PER_CELL, POLICIES, SCENARIOS,
                                       SPEC, configurations, output_path)
from scripts.verify_sources import ROOT, load_index, verify_result


def select_candidates(counts):
    """Rank non-control policies by worst cell, then sum, then identifier."""
    candidates = sorted(name for name in POLICIES if name != 'bare')
    if (not isinstance(counts, dict) or set(counts) != set(SCENARIOS)
            or any(not isinstance(counts[scenario], dict) or set(counts[scenario]) != set(POLICIES)
                   for scenario in SCENARIOS)
            or any(type(counts[scenario][name]) is not int or not 0 <= counts[scenario][name] <= N_PER_CELL
                   for scenario in SCENARIOS for name in POLICIES)):
        raise ValueError('A complete preregistered win-count matrix is required')
    return tuple(sorted(candidates, key=lambda name: (
        -min(counts[scenario][name] for scenario in SCENARIOS),
        -sum(counts[scenario][name] for scenario in SCENARIOS), name))[:2])


def load_cells():
    index = load_index(ROOT)
    input_bytes = tuple(path.read_bytes() for path in INPUTS)
    hero, policies, scenarios = configurations(input_bytes)
    specification_sha = sha256(SPEC.read_bytes()).hexdigest()
    source_commits, inputs, counts, descriptive = set(), {}, {}, {}
    for scenario in SCENARIOS:
        counts[scenario], descriptive[scenario] = {}, {}
        opponent, opponent_policy, distance, board = scenarios[scenario]
        for policy_name in POLICIES:
            path = output_path(scenario, policy_name)
            mode, issues = verify_result(path, root=ROOT, index=index)
            if issues:
                raise ValueError(f'{path.name}: frozen source verification failed: {issues}')
            raw = path.read_bytes()
            digest = sha256(raw).hexdigest()
            if digest != index[path.name]['result_sha256']:
                raise ValueError(f'{path.name}: bytes changed during verification')
            record = json.loads(raw)
            study = record.get('study', {})
            expected_distance = board.distance if board else distance
            expected_board = board.record() if board else None
            if (record.get('schema') != 'blacklight-generic-character-batch-v1'
                    or record.get('table_ruleset') != 'split_fast_v3'
                    or record.get('n') != N_PER_CELL or record.get('master_seed') != MASTER_SEED
                    or record.get('max_rounds') != 30 or record.get('initial_distance') != expected_distance
                    or record.get('battlefield') != expected_board
                    or record.get('sheets') != [sheet_record(hero), sheet_record(opponent)]
                    or record.get('policies') != [asdict(policies[policy_name]), asdict(opponent_policy)]
                    or record.get('policy_types') != _policy_types((policies[policy_name], opponent_policy))
                    or study.get('phase') != 'development' or study.get('scenario_id') != scenario
                    or study.get('policy_id') != policy_name or study.get('pre_registered_n') != N_PER_CELL
                    or study.get('n_matches_preregistration') is not True
                    or study.get('source_commit') != index[path.name]['source_commit']
                    or record.get('source_sha256', {}).get(SPEC.relative_to(ROOT).as_posix()) != specification_sha
                    or recorded_contract_status(record) != 'recorded_verified'
                    or record.get('extended_metrics_schema') != 'blacklight-batch-combat-samples-v1'):
                raise ValueError(f'{path.name}: preregistered configuration mismatch')
            issues = audit_batch_metadata(record)
            if issues:
                raise ValueError(f'{path.name}: batch audit failed: {issues}')
            source_commits.add(study['source_commit'])
            inputs[path.relative_to(ROOT).as_posix()] = digest
            counts[scenario][policy_name] = record['outcomes']['win']
            descriptive[scenario][policy_name] = {
                'outcomes': record['outcomes'], 'rates': record['rates'],
                'metrics_all_starts': record['extended_metrics_all_starts']}
    if len(source_commits) != 1:
        raise ValueError('Development cells do not share one source commit')
    return counts, descriptive, inputs, next(iter(source_commits)), specification_sha


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to((ROOT / 'results').resolve()):
        parser.error('Selection output belongs outside the frozen batch results directory')
    require_new_output(args.output)
    counts, descriptive, inputs, commit, spec_hash = load_cells()
    finalists = select_candidates(counts)
    script = Path(__file__).resolve()
    before = {**inputs, SPEC.relative_to(ROOT).as_posix(): spec_hash,
              script.relative_to(ROOT).as_posix(): sha256(script.read_bytes()).hexdigest()}
    after = {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in before}
    require_unchanged_sources(before, after)
    payload = {'schema': 'blacklight-current-duel-development-selection-v1',
               'phase': 'development', 'source_commit': commit,
               'pre_registered_rule': 'maximize minimum wins; then total wins; then policy ID',
               'finalists': list(finalists), 'control': 'bare', 'n_per_cell': N_PER_CELL,
               'master_seed': MASTER_SEED, 'input_sha256': before,
               'win_counts': counts, 'descriptive': descriptive,
               'limitations': ['exploratory selection, not a confirmatory comparison',
                               'synthetic physical opponents, no Focus attacks or full game coverage',
                               'different cells use separate seeds; not paired samples']}
    write_new_text(args.output, json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print('Exploratory selection recorded; confirmation and holdout remain unexecuted.')


if __name__ == '__main__':
    main()
