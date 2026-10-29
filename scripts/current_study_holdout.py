"""Run the fixed holdout scenarios after freezing the confirmation."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from pathlib import Path

from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.runner import run_batch
from combatants.sheets import parse_sheet, sheet_record
from combatants.split_fast import SplitFastPolicy
from scripts.current_study_analysis import load_confirmation
from scripts.current_study_confirm import (FINALISTS, N_PER_CELL, POLICIES, SELECTION,
                                           assert_seed_separation, confirmation_cell_hash,
                                           validated_selection)
from scripts.current_study_dev import (INPUTS, ROOT, configurations, declared_sources,
                                       source_commit)

MASTER_SEED = 827104293
SPEC = ROOT / 'CURRENT_DUEL_HOLDOUT_SPEC.md'
ANALYSIS = ROOT / 'experiments/current_duel_study/confirmation_analysis_v1.json'
SCENARIOS = ('mirror_blade', 'rank4_sturdy2', 'gunner_open')


def holdout_configurations(input_bytes):
    hero, policies, base = configurations(input_bytes)
    mirror_data = sheet_record(hero)
    mirror_data.update(id='synthetic_victor_mirror_blade', revision='holdout-blade-v1',
                       name='Espelho sintético com Lâmina')
    mirror_data['provenance'].append({'kind': 'synthetic', 'purpose': 'Holdout mirror, not an official NPC'})
    mirror_data['notes'].append('Synthetic mirror uses the same biological arsenal as Victor.')
    mirror = parse_sheet(mirror_data)
    bruiser_data = sheet_record(base['rank4'][0])
    bruiser_data.update(id='synthetic_rank4_sturdy2', revision='holdout-sturdy2-v1',
                        name='Exemplo Rank 4 Sturdy 2')
    sturdy = [feature for feature in bruiser_data['features'] if feature['id'] == 'sturdy']
    if len(sturdy) != 1 or sturdy[0]['level'] != 1:
        raise ValueError('Base synthetic Sturdy is not the preregistered level')
    sturdy[0]['level'] = 2
    bruiser_data['notes'].append('Synthetic holdout changes Sturdy 1 to 2; build legality is not certified.')
    bruiser = parse_sheet(bruiser_data)
    gunner = base['gunner_corridor'][0]
    scenarios = {
        'mirror_blade': (mirror, SplitFastPolicy('holdout_mirror_blade', weapon='blade', offhand='hammer',
                                                  prefer_fast=True, effect_limb=0, shield_react=True,
                                                  shield_end_turn=True, riposte=True, knockback_stance=False), 4, None),
        'rank4_sturdy2': (bruiser, SplitFastPolicy('holdout_rank4_unarmed', riposte=False,
                                                   knockback_stance=False), 1, None),
        'gunner_open': (gunner, SplitFastPolicy('holdout_gunner_open', kite=True, move_after_attack=True,
                                                treat_bleeding=True, riposte=False, knockback_stance=False),
                        8, None),
    }
    return hero, policies, scenarios


def prior_inputs():
    selection = validated_selection()
    _, confirmation_inputs, _ = load_confirmation()
    analysis_raw = ANALYSIS.read_bytes()
    analysis = json.loads(analysis_raw)
    if (analysis.get('schema') != 'blacklight-current-duel-confirmation-analysis-v1'
            or any(analysis.get('input_sha256', {}).get(name) != digest
                   for name, digest in confirmation_inputs.items())):
        raise ValueError('Confirmation analysis does not match the frozen input cells')
    sources = {**selection['input_sha256'], **confirmation_inputs}
    for path in (SELECTION, ANALYSIS, SPEC, Path(__file__).resolve()):
        sources[path.relative_to(ROOT).as_posix()] = sha256(path.read_bytes()).hexdigest()
    return sources


def assert_all_seeds():
    selection = validated_selection()
    assert_seed_separation(selection)
    prior = set()
    for name in selection['input_sha256']:
        if name.startswith('results/current_duel_dev_v1_'):
            record = json.loads((ROOT / name).read_text(encoding='utf-8'))
            prior.update(trace['seed'] for trace in record['audited_traces'])
    _, confirmation_inputs, _ = load_confirmation()
    for name in confirmation_inputs:
        record = json.loads((ROOT / name).read_text(encoding='utf-8'))
        prior.update(trace['seed'] for trace in record['audited_traces'])
    if len(prior) != 135000:
        raise ValueError('Previous seed inventory is incomplete or contains collisions')
    hero, policies, scenarios = holdout_configurations(tuple(path.read_bytes() for path in INPUTS))
    new = set()
    for scenario in SCENARIOS:
        opponent, opponent_policy, distance, board = scenarios[scenario]
        for policy_name in POLICIES:
            cell_hash = confirmation_cell_hash(hero, opponent, policies[policy_name], opponent_policy,
                                               distance, board)
            for index in range(N_PER_CELL):
                key = f'character-batch-v2|{MASTER_SEED}|{cell_hash}|{index}'
                seed = int.from_bytes(sha256(key.encode()).digest()[:8], 'big')
                if seed in prior or seed in new:
                    raise ValueError('Holdout seed collision')
                new.add(seed)
    return len(prior), len(new)


def output_path(scenario, policy):
    return ROOT / 'results' / f'current_duel_holdout_v1_{scenario}_{policy}.json'


def execute_cell(scenario, policy_name, *, n=N_PER_CELL, output=None):
    if scenario not in SCENARIOS or policy_name not in POLICIES or type(n) is not int or n < 1:
        raise ValueError('Invalid holdout cell')
    path = output_path(scenario, policy_name) if output is None else Path(output)
    require_new_output(path)
    prior_count, new_count = assert_all_seeds()
    before_bytes = tuple(path.read_bytes() for path in INPUTS)
    hero, policies, scenarios = holdout_configurations(before_bytes)
    opponent, opponent_policy, distance, board = scenarios[scenario]
    policy = policies[policy_name]
    sources = {**declared_sources((policy, opponent_policy), board, before_bytes), **prior_inputs()}
    commit = source_commit(sources)
    result = run_batch(hero, opponent, policy, opponent_policy, n=n, master_seed=MASTER_SEED,
                       initial_distance=distance, max_rounds=30, audit_every=1,
                       battlefield=board, extended_metrics=True)
    after_bytes = tuple(path.read_bytes() for path in INPUTS)
    require_unchanged_sources(sources, {**declared_sources((policy, opponent_policy), board, after_bytes),
                                        **prior_inputs()})
    if source_commit(sources) != commit:
        raise RuntimeError('Holdout source commit changed during execution')
    result['source_sha256'].update(sources)
    result['study'] = {'phase': 'holdout', 'scenario_id': scenario, 'policy_id': policy_name,
                       'source_commit': commit, 'spec': SPEC.relative_to(ROOT).as_posix(),
                       'pre_registered_n': N_PER_CELL, 'n_matches_preregistration': n == N_PER_CELL,
                       'seed_preflight': {'previous': prior_count, 'holdout': new_count, 'collisions': 0},
                       'finalists': list(FINALISTS), 'interpretation': 'synthetic holdout, not global optimality'}
    write_new_text(path, json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--scenario', choices=SCENARIOS)
    parser.add_argument('--policy', choices=POLICIES)
    args = parser.parse_args()
    if args.all and not (args.scenario or args.policy):
        cells = tuple((scenario, policy) for scenario in SCENARIOS for policy in POLICIES)
    elif not args.all and args.scenario and args.policy:
        cells = ((args.scenario, args.policy),)
    else:
        parser.error('Use --all or both --scenario and --policy')
    for scenario, policy in cells:
        require_new_output(output_path(scenario, policy))
    previous, new = assert_all_seeds()
    print(f'Seed preflight: {previous} prior, {new} holdout; no collisions.', flush=True)
    for number, (scenario, policy) in enumerate(cells, 1):
        print(f'Reserva {number}/{len(cells)}: {scenario}, {policy}', flush=True)
        execute_cell(scenario, policy)
    print('Holdout cells complete; freeze before analysis.', flush=True)


if __name__ == '__main__':
    main()
