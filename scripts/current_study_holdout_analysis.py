"""Analyze only the frozen, preregistered physical-duel holdout cells."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.batch_audit import audit_batch_metadata
from blacklight.experiment import wilson
from blacklight.mechanics_contract import recorded_contract_status
from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.runner import _policy_types
from combatants.sheets import sheet_record
from scripts.current_study_analysis import ALPHA, PAIRS, compare, load_confirmation
from scripts.current_study_confirm import FINALISTS, N_PER_CELL, POLICIES, SELECTION, validated_selection
from scripts.current_study_dev import INPUTS, ROOT, source_commit
from scripts.current_study_holdout import (ANALYSIS, MASTER_SEED, SCENARIOS, SPEC,
                                           holdout_configurations, output_path)
from scripts.verify_sources import load_index, verify_result


def load_holdout():
    selection = validated_selection()
    _, confirmation, _ = load_confirmation()
    prior_analysis = json.loads(ANALYSIS.read_bytes())
    if (prior_analysis.get('schema') != 'blacklight-current-duel-confirmation-analysis-v1'
            or any(prior_analysis.get('input_sha256', {}).get(name) != digest
                   for name, digest in confirmation.items())):
        raise ValueError('Prior analysis does not match frozen confirmation')
    index = load_index(ROOT)
    hero, policies, scenarios = holdout_configurations(tuple(p.read_bytes() for p in INPUTS))
    previous = set()
    for name in (*selection['input_sha256'], *confirmation):
        if name.startswith(('results/current_duel_dev_v1_', 'results/current_duel_confirm_v1_')):
            record = json.loads((ROOT / name).read_text(encoding='utf-8'))
            for trace in record['audited_traces']:
                if trace['seed'] in previous:
                    raise ValueError('Prior seeds are not unique')
                previous.add(trace['seed'])
    if len(previous) != 135000:
        raise ValueError('Prior seed inventory is incomplete')
    sources, commits, seen, cells = {}, set(), set(), {}
    spec_hash = sha256(SPEC.read_bytes()).hexdigest()
    for scenario in SCENARIOS:
        cells[scenario] = {}
        opponent, foe_policy, distance, board = scenarios[scenario]
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
                    or record.get('max_rounds') != 30 or record.get('initial_distance') != distance
                    or record.get('battlefield') is not None
                    or record.get('sheets') != [sheet_record(hero), sheet_record(opponent)]
                    or record.get('policies') != [asdict(policies[name]), asdict(foe_policy)]
                    or record.get('policy_types') != _policy_types((policies[name], foe_policy))
                    or study.get('phase') != 'holdout' or study.get('scenario_id') != scenario
                    or study.get('policy_id') != name or study.get('pre_registered_n') != N_PER_CELL
                    or study.get('spec') != SPEC.relative_to(ROOT).as_posix()
                    or study.get('finalists') != list(FINALISTS)
                    or study.get('n_matches_preregistration') is not True
                    or study.get('source_commit') != index[path.name]['source_commit']
                    or study.get('seed_preflight') != {'previous': 135000, 'holdout': 120000, 'collisions': 0}
                    or record.get('source_sha256', {}).get(SPEC.relative_to(ROOT).as_posix()) != spec_hash
                    or record.get('source_sha256', {}).get(ANALYSIS.relative_to(ROOT).as_posix()) != sha256(ANALYSIS.read_bytes()).hexdigest()
                    or record.get('source_sha256', {}).get(SELECTION.relative_to(ROOT).as_posix()) != sha256(SELECTION.read_bytes()).hexdigest()
                    or recorded_contract_status(record) != 'recorded_verified'
                    or record.get('extended_metrics_schema') != 'blacklight-batch-combat-samples-v1'):
                raise ValueError(f'{path.name}: preregistered configuration mismatch')
            issues = audit_batch_metadata(record)
            if issues:
                raise ValueError(f'{path.name}: batch audit failed: {issues}')
            for trace in record['audited_traces']:
                seed = trace['seed']
                if seed in seen or seed in previous:
                    raise ValueError('Duplicate or overlapping holdout seed')
                seen.add(seed)
            commits.add(study['source_commit'])
            sources[path.relative_to(ROOT).as_posix()] = digest
            wins = record['outcomes']['win']
            cells[scenario][name] = {'n': N_PER_CELL, 'win_rate': wins / N_PER_CELL,
                                     'outcomes': record['outcomes'],
                                     'wilson_95': list(wilson(wins, N_PER_CELL)),
                                     'metrics_all_starts': record['extended_metrics_all_starts']}
    if len(commits) != 1 or len(seen) != 120000:
        raise ValueError('Holdout commits or seed inventory are inconsistent')
    return cells, sources, next(iter(commits))


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
    cells, inputs, commit = load_holdout()
    comparisons = {scenario: [{'first': a, 'second': b, **compare(cells[scenario][a], cells[scenario][b])}
                              for a, b in PAIRS] for scenario in SCENARIOS}
    refs = (SELECTION, ANALYSIS, SPEC, script)
    before = {**inputs, **{p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()).hexdigest() for p in refs}}
    require_unchanged_sources(before, {name: sha256((ROOT / name).read_bytes()).hexdigest() for name in before})
    if source_commit(script_hash) != analysis_commit:
        raise RuntimeError('Analysis source commit changed')
    payload = {'schema': 'blacklight-current-duel-holdout-analysis-v1',
               'source_commit': commit, 'analysis_commit': analysis_commit,
               'n_per_cell': N_PER_CELL, 'alpha_per_comparison': ALPHA,
               'input_sha256': before, 'cells': cells, 'comparisons': comparisons,
               'limitations': ['synthetic physical duels, not all encounters',
                               'coverage assumes independent Bernoulli starts',
                               'individual Wilson intervals are descriptive, not simultaneous']}
    write_new_text(args.output, json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print('Holdout analysis recorded.')


if __name__ == '__main__':
    main()
