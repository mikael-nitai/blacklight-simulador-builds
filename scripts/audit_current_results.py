"""Recheck the six frozen current-rule controls without writing new results.

Complete duel logs are compared event by event. Batch records retain seeds and
aggregates, not every original log, so their comparisons have narrower scope.
"""

from collections import Counter
from hashlib import sha256
import json
from math import isclose, sqrt

from blacklight.audit import audit_profiled_log
from blacklight.policies import RulePolicy
from blacklight.rulesets import CURRENT_RULESET
from combatants.battlefields import CorridorMap
from combatants.duel_adapter import compile_duel
from combatants.runner import run_batch, run_duel
from combatants.sheets import parse_sheet
from combatants.split_fast import SplitFastDuel, SplitFastPolicy
from combatants.terrain_policies import WallAwarePolicy
from .verify_sources import ROOT, load_index, verify_result


DUELS = (
    'split_fast_v3_blade_effects_demo.json',
    'split_fast_v3_hammer_effects_demo.json',
    'current_corridor_v1_blade_effects_demo.json',
    'current_corridor_v1_hammer_effects_demo.json',
)
CORRIDOR_BATCH = 'current_corridor_v1_integration_batch.json'
EARLY_BATCH = 'split_fast_v3_rank4_integration_batch.json'
POLICY_TYPES = {
    ('blacklight.policies', 'RulePolicy'): RulePolicy,
    ('combatants.split_fast', 'SplitFastPolicy'): SplitFastPolicy,
    ('combatants.terrain_policies', 'WallAwarePolicy'): WallAwarePolicy,
}


def load_frozen(name: str, index: dict) -> dict:
    path = ROOT / 'results' / name
    _, issues = verify_result(path, root=ROOT, index=index)
    if issues:
        raise ValueError(f'{name}: frozen source verification failed: {issues}')
    content = path.read_bytes()
    if sha256(content).hexdigest() != index[name]['result_sha256']:
        raise ValueError(f'{name}: result changed after verification')
    return json.loads(content)


def configuration(saved: dict):
    sheets = tuple(parse_sheet(item) for item in saved['sheets'])
    declared = saved.get('policy_types')
    policies = []
    for index, params in enumerate(saved['policies']):
        if declared:
            key = (declared[index]['module'], declared[index]['class'])
        else:
            key = (('combatants.split_fast', 'SplitFastPolicy') if 'effect_limb' in params
                   else ('blacklight.policies', 'RulePolicy'))
        if key not in POLICY_TYPES:
            raise ValueError(f'Unknown policy type in saved control: {key}')
        policies.append(POLICY_TYPES[key](**params))
    terrain = saved.get('battlefield')
    board = (CorridorMap(terrain['length'], tuple(terrain['initial_positions']))
             if terrain else None)
    return sheets, tuple(policies), board


def normalized(value):
    return json.loads(json.dumps(value))


def audit_duel(saved: dict) -> None:
    sheets, policies, board = configuration(saved)
    current = run_duel(*sheets, *policies, seed=saved['seed'],
                       initial_distance=saved['initial_distance'],
                       max_rounds=saved['max_rounds'], battlefield=board)
    for field in ('result', 'hero_outcome'):
        if normalized(current[field]) != saved[field]:
            raise AssertionError(f'Current duel replay differs in {field}')


def audit_corridor_batch(saved: dict) -> int:
    sheets, policies, board = configuration(saved)
    if [row['index'] for row in saved['audited_traces']] != list(range(saved['n'])):
        raise ValueError('Expected a recorded seed for every corridor start')
    current = run_batch(*sheets, *policies, n=saved['n'], master_seed=saved['master_seed'],
                        initial_distance=saved['initial_distance'], max_rounds=saved['max_rounds'],
                        audit_every=1, battlefield=board)
    for field in ('outcomes', 'rates', 'metrics_all_starts', 'audited_traces',
                  'cell_sha256', 'spatial_counts_all_starts'):
        if normalized(current[field]) != saved[field]:
            raise AssertionError(f'Current corridor batch differs in {field}')
    return saved['n']


def audit_early_batch(saved: dict) -> int:
    """Replay recorded v1 seeds; v2 now adds policy types to seed identity."""
    sheets, policies, board = configuration(saved)
    if board is not None:
        raise ValueError('The early fixed-contact batch must not contain a map')
    profiles = tuple(compile_duel(sheet) for sheet in sheets)
    traces = saved['audited_traces']
    if type(saved['n']) is not int or saved['n'] < 2:
        raise ValueError('Early-batch variance comparison requires at least two starts')
    if [row['index'] for row in traces] != list(range(saved['n'])):
        raise ValueError('Expected a recorded seed for every early-batch start')
    outcomes = Counter()
    values = {name: [] for name in ('rounds', 'hero_final_health', 'hero_final_focus',
                                    'hero_damage_dealt', 'hero_damage_taken')}
    for trace in traces:
        key = f"character-batch-v1|{saved['master_seed']}|{saved['cell_sha256']}|{trace['index']}"
        seed = int.from_bytes(sha256(key.encode()).digest()[:8], 'big')
        if seed != trace['seed']:
            raise AssertionError(f"Recorded v1 seed disagrees at index {trace['index']}")
        battle = SplitFastDuel(profiles, policies, seed=seed, audit=True,
                               initial_distance=saved['initial_distance'], max_rounds=saved['max_rounds'])
        result = battle.run()
        issues = audit_profiled_log(result.log, profiles, ruleset=CURRENT_RULESET)
        if issues:
            raise AssertionError(f"Audit failed at index {trace['index']}: {issues[:3]}")
        outcome = (result.outcome if result.outcome in ('draw', 'inconclusive') else
                   'win' if result.winner == profiles[0].name else 'loss')
        outcomes[outcome] += 1
        for name, value in (
            ('rounds', result.rounds), ('hero_final_health', result.final_health[0]),
            ('hero_final_focus', result.final_focus[0]),
            ('hero_damage_dealt', result.metrics[0]['damage_dealt']),
            ('hero_damage_taken', result.metrics[0]['damage_taken']),
        ):
            values[name].append(value)
    if any(outcomes[name] != count for name, count in saved['outcomes'].items()):
        raise AssertionError('Early-batch outcome counts changed')
    for name, sample in values.items():
        mean = sum(sample) / len(sample)
        variance = max(0.0, (sum(value * value for value in sample) - len(sample) * mean * mean)
                       / (len(sample) - 1))
        expected = saved['metrics_all_starts'][name]
        if (not isclose(mean, expected['mean'], rel_tol=0, abs_tol=1e-12)
                or not isclose(sqrt(variance / len(sample)), expected['mc_se'],
                               rel_tol=0, abs_tol=1e-12)):
            raise AssertionError(f'Early-batch summary changed: {name}')
    return len(traces)


def main() -> None:
    index = load_index()
    saved = {name: load_frozen(name, index) for name in (*DUELS, CORRIDOR_BATCH, EARLY_BATCH)}
    for name in DUELS:
        audit_duel(saved[name])
    corridor_starts = audit_corridor_batch(saved[CORRIDOR_BATCH])
    early_starts = audit_early_batch(saved[EARLY_BATCH])
    print(json.dumps({
        'status': 'pass', 'complete_duel_logs_matching': len(DUELS),
        'corridor_batch_starts': corridor_starts, 'early_batch_starts': early_starts,
        'limits': ['Batch originals contain seeds and aggregates, not every original full log.',
                   'Matching replays do not establish the correctness of all game rules.'],
    }, indent=2))


if __name__ == '__main__':
    main()
