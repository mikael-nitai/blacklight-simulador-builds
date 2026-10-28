"""Run preregistered exploratory physical duels under current table rules."""

from argparse import ArgumentParser
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from blacklight.experiment import ROOT
from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.battlefields import CorridorMap
from combatants.runner import _source_manifest, run_batch
from combatants.sheets import parse_sheet, sheet_record
from combatants.split_fast import SplitFastPolicy
from combatants.terrain_policies import WallAwarePolicy
from scripts.verify_sources import snapshot_source_hash


MASTER_SEED = 827104291
N_PER_CELL = 1000
SPEC = ROOT / 'CURRENT_DUEL_STUDY_SPEC.md'
INPUTS = (ROOT / 'characters/victor_halle/rank3_2026-10-27_split_fast.json',
          ROOT / 'characters/examples/synthetic_rank4_split_fast.json',
          ROOT / 'characters/examples/synthetic_rank4_nonammo_gunner.json')
POLICIES = {
    'bare': dict(weapon='bare'),
    'hammer': dict(weapon='hammer'),
    'hammer_fast_hammer': dict(weapon='hammer', offhand='blade', prefer_fast=True, effect_limb=0),
    'hammer_fast_blade': dict(weapon='hammer', offhand='blade', prefer_fast=True, effect_limb=1),
    'blade_fast_blade': dict(weapon='blade', offhand='hammer', prefer_fast=True, effect_limb=0),
}
SCENARIOS = ('mirror', 'rank4', 'gunner_corridor')


def configurations(input_bytes):
    hero, bruiser, gunner = tuple(parse_sheet(json.loads(data.decode('utf-8'))) for data in input_bytes)
    mirror_data = sheet_record(hero)
    mirror_data.update(id='synthetic_victor_mirror', revision='current-study-mirror-v1',
                       name='Espelho sintético de Victor')
    mirror_data['provenance'].append({'kind': 'synthetic',
                                      'purpose': 'Hypothetical mirror of the supplied Victor sheet, not an official NPC'})
    mirror_data['notes'].append('Synthetic opponent assumes the same biological arsenal as Victor for this scenario.')
    mirror = parse_sheet(mirror_data)
    common = {'shield_react': True, 'riposte': True, 'knockback_stance': False}
    candidates = {name: SplitFastPolicy(name, **common, **params) for name, params in POLICIES.items()}
    scenarios = {
        'mirror': (mirror, SplitFastPolicy('mirror_hammer_fast_shield', weapon='hammer', offhand='blade',
                                          prefer_fast=True, effect_limb=0, **common), 1, None),
        'rank4': (bruiser, SplitFastPolicy('rank4_unarmed', riposte=False, knockback_stance=False), 1, None),
        'gunner_corridor': (gunner, WallAwarePolicy('gunner_wall_aware', kite=True,
                                                   move_after_attack=True, treat_bleeding=True,
                                                   riposte=False, knockback_stance=False),
                            None, CorridorMap(12, (0, 8))),
    }
    return hero, candidates, scenarios


def declared_sources(policies, battlefield, input_bytes):
    sources = _source_manifest(policies, battlefield)
    for path, content in zip(INPUTS, input_bytes):
        sources[path.relative_to(ROOT).as_posix()] = sha256(content).hexdigest()
    for path in (SPEC, Path(__file__).resolve()):
        sources[path.relative_to(ROOT).as_posix()] = sha256(path.read_bytes()).hexdigest()
    return sources


def source_commit(sources):
    result = subprocess.run(['git', '--no-replace-objects', 'rev-parse', '--verify', 'HEAD^{commit}'],
                            cwd=ROOT, check=True, capture_output=True, text=True)
    commit = result.stdout.strip()
    for name, expected in sources.items():
        if snapshot_source_hash(ROOT, commit, name) != expected:
            raise RuntimeError(f'Study source is not the committed version: {name}')
    return commit


def output_path(scenario, policy):
    return ROOT / 'results' / f'current_duel_dev_v1_{scenario}_{policy}.json'


def execute_cell(scenario_id, policy_id, *, n=N_PER_CELL, output=None):
    if scenario_id not in SCENARIOS or policy_id not in POLICIES or type(n) is not int or n < 1:
        raise ValueError('Unknown preregistered cell or invalid count')
    path = output_path(scenario_id, policy_id) if output is None else Path(output)
    require_new_output(path)
    input_bytes = tuple(path.read_bytes() for path in INPUTS)
    hero, policies, scenarios = configurations(input_bytes)
    opponent, opponent_policy, distance, board = scenarios[scenario_id]
    policy = policies[policy_id]
    sources = declared_sources((policy, opponent_policy), board, input_bytes)
    commit = source_commit(sources)
    payload = run_batch(hero, opponent, policy, opponent_policy, n=n, master_seed=MASTER_SEED,
                        initial_distance=distance, max_rounds=30, audit_every=1,
                        battlefield=board, extended_metrics=True)
    now_bytes = tuple(input_path.read_bytes() for input_path in INPUTS)
    require_unchanged_sources(sources, declared_sources((policy, opponent_policy), board, now_bytes))
    if source_commit(sources) != commit:
        raise RuntimeError('Study source commit changed during execution')
    payload['source_sha256'].update(sources)
    payload['study'] = {'phase': 'development', 'scenario_id': scenario_id, 'policy_id': policy_id,
                        'spec': SPEC.relative_to(ROOT).as_posix(), 'source_commit': commit,
                        'pre_registered_n': N_PER_CELL, 'n_matches_preregistration': n == N_PER_CELL,
                        'interpretation': 'exploratory, limited synthetic physical duels'}
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    return payload


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--all', action='store_true', help='Run all preregistered development cells')
    parser.add_argument('--scenario', choices=SCENARIOS)
    parser.add_argument('--policy', choices=tuple(POLICIES))
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
        print(f'Desenvolvimento {index}/{len(cells)}: {scenario}, {policy}', flush=True)
        execute_cell(scenario, policy)
    print('Development cells finished; results remain exploratory.', flush=True)


if __name__ == '__main__':
    main()
