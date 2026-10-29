"""Run the fixed exploratory Ram/partial-Crossbones protocol, auditing every complete duel."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.engine import Move
from blacklight.experiment import wilson
from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.runner import _source_manifest
from combatants.sheets import load_sheet, sheet_record
from experimental.crossbones_subset import build_crossbones_stopping_subset
from experimental.ram_incapacity_duel import RamDeathUndecided
from experimental.stopping_audit import audit_stopping_duel
from experimental.stopping_duel import StoppingPolicy
from experimental.stopping_ram_duel import StoppingRamDuel
from scripts.crossbones_ram_demo import EVIDENCE, EXTRA as RAM_SOURCES, VICTOR
from scripts.current_study_dev import ROOT, source_commit
from scripts.audit_ram_crossbones_explore import audit as audit_exploration

SPEC = ROOT / 'RAM_CROSSBONES_EXPLORATION_SPEC.md'
MODE = 'stop_before_heal_reject_lethal'
N_PER_CELL = 1000
MAX_ROUNDS = 30
DISTANCE = 10
SCENARIOS = ('stationary', 'kite')
STRATEGIES = ('hammer', 'fast_hammer', 'fast_blade')
RAM_CHOICES = (False, True)
EXTRA = tuple(sorted(set(RAM_SOURCES + ('RAM_CROSSBONES_EXPLORATION_SPEC.md',
                'scripts/ram_crossbones_explore.py', 'scripts/audit_ram_crossbones_explore.py',
                'scripts/replay_ram_crossbones_explore.py'))))


class StationaryPolicy(StoppingPolicy):
    def choose_move(self, observation):
        return Move()

    def choose_post_move(self, observation):
        return Move()


def seed_for(scenario, index):
    if scenario not in SCENARIOS or type(index) is not int or not 0 <= index < N_PER_CELL:
        raise ValueError('Unknown preregistered seed coordinate')
    value = f'blacklight-ram-crossbones-explore-v1:{scenario}:{index}'.encode('utf-8')
    return int.from_bytes(sha256(value).digest()[:8], 'big')


def policies_for(scenario, strategy, use_ram):
    if scenario not in SCENARIOS or strategy not in STRATEGIES or type(use_ram) is not bool:
        raise ValueError('Unknown preregistered cell')
    common = dict(prefer_stopping=True, use_ram=False, treat_bleeding=True)
    if scenario == 'stationary':
        foe = StationaryPolicy('crossbones_parcial_estacionario', **common)
    else:
        foe = StoppingPolicy('crossbones_parcial_recuo', kite=True, move_after_attack=True, **common)
    hero = StoppingPolicy('victor_' + strategy, weapon='hammer',
                          offhand='blade' if strategy != 'hammer' else None,
                          prefer_fast=strategy != 'hammer', effect_limb=int(strategy == 'fast_blade'),
                          use_ram=use_ram, shield_react=True, knockback_stance=False)
    return foe, hero


def sources(policies):
    source = _source_manifest(policies, None)
    source.update({name: sha256((ROOT / name).read_bytes()).hexdigest() for name in EXTRA})
    return source


def policy_type(policy):
    if isinstance(policy, StationaryPolicy):
        return {'module': 'scripts.ram_crossbones_explore', 'class': 'StationaryPolicy'}
    return {'module': type(policy).__module__, 'class': type(policy).__qualname__}


def digest(value):
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=sorted)
    return sha256(data.encode('utf-8')).hexdigest()


def simulate(profiles, policies, weapon, seed):
    duel = StoppingRamDuel(profiles, policies, seed=seed, initial_prone=(False, False),
                           initial_distance=DISTANCE, max_rounds=MAX_ROUNDS, audit=True,
                           action_registry=DEFAULT_ACTIONS, ranged_weapons=(weapon, 'generic'),
                           stop_on_attacker=profiles[1].name)
    try:
        result = duel.run()
    except RamDeathUndecided as error:
        if (error.actor != profiles[1].name or type(error.raw_health_after) is not int
                or error.death_threshold != -profiles[1].max_health
                or error.raw_health_after > error.death_threshold):
            raise RuntimeError('Invalid unresolved Ram boundary') from error
        return {'seed': seed, 'status': 'unresolved_death_threshold',
                'raw_health_after': error.raw_health_after, 'death_threshold': error.death_threshold,
                'prefix_sha256': digest(duel.log), 'audit': 'incomplete_prefix_replay_required'}
    issues = audit_stopping_duel(result, profiles, ranged_weapons=(weapon, 'generic'),
                                 initial_prone=(False, False), initial_distance=DISTANCE,
                                 expected_seed=seed, max_rounds=MAX_ROUNDS, ruleset=duel.table_ruleset,
                                 self_damage_mode=MODE, stop_on_attacker=profiles[1].name)
    if issues:
        raise RuntimeError(f'Seed {seed} failed independent audit: {issues}')
    if result.outcome == 'win':
        if result.winner not in (profiles[0].name, profiles[1].name):
            raise RuntimeError('Unexpected winning combatant')
        status = 'victory' if result.winner == profiles[1].name else 'defeat'
    elif result.outcome in ('draw', 'inconclusive') and result.winner is None:
        status = result.outcome
    else:
        raise RuntimeError('Unknown battle outcome')
    return {'seed': seed, 'status': status, 'rounds': result.rounds, 'turns': result.turns,
            'final_health': list(result.final_health), 'final_focus': list(result.final_focus),
            'opponent_metrics': result.metrics[0], 'victor_metrics': result.metrics[1],
            'ram_attacks': sum(event['type'] == 'ram_attack' for event in result.log),
            'stopping_uses': sum(event['type'] == 'stopping_start' for event in result.log),
            'parries': sum(event['type'] == 'parry_start' for event in result.log),
            'result_sha256': digest(asdict(result)), 'audit': 'complete_duel_passed'}


def summarize(records):
    statuses = ('victory', 'defeat', 'draw', 'inconclusive', 'unresolved_death_threshold')
    counts = {status: sum(row['status'] == status for row in records) for status in statuses}
    n = len(records)
    if n < 1 or sum(counts.values()) != n:
        raise ValueError('Records contain an invalid status or no starts')
    return {'n': n, 'counts': counts, 'recorded_victory_fraction': counts['victory'] / n,
            'victory_identification_bounds': [counts['victory'] / n,
                (counts['victory'] + counts['unresolved_death_threshold']) / n],
            'recorded_victory_wilson_95': list(wilson(counts['victory'], n))}


def run(output, *, n=N_PER_CELL):
    path = Path(output)
    if path.resolve().is_relative_to((ROOT / 'results').resolve()):
        raise ValueError('Experimental results must not enter the certified results inventory')
    if type(n) is not int or not 1 <= n <= N_PER_CELL:
        raise ValueError('Invalid sample size')
    require_new_output(path)
    evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
    subset = build_crossbones_stopping_subset(evidence, accept_incomplete=True)
    victor_sheet = load_sheet(VICTOR)
    profiles = (subset.profile, compile_duel(victor_sheet))
    all_policies = tuple(policy for scenario in SCENARIOS for strategy in STRATEGIES
                         for use_ram in RAM_CHOICES for policy in policies_for(scenario, strategy, use_ram))
    before = sources(all_policies)
    commit = source_commit(before)
    seeds = [seed_for(scenario, index) for scenario in SCENARIOS for index in range(n)]
    if len(seeds) != len(set(seeds)):
        raise RuntimeError('Unexpected seed collision across scenario coordinates')
    cells = []
    for scenario in SCENARIOS:
        for strategy in STRATEGIES:
            for use_ram in RAM_CHOICES:
                policies = policies_for(scenario, strategy, use_ram)
                rows = []
                for index in range(n):
                    row = simulate(profiles, policies, subset.ranged_weapon, seed_for(scenario, index))
                    row['index'] = index
                    if row['status'] == 'unresolved_death_threshold':
                        replay = simulate(profiles, policies, subset.ranged_weapon, row['seed'])
                        if any(replay.get(key) != row.get(key) for key in
                               ('status', 'raw_health_after', 'death_threshold', 'prefix_sha256')):
                            raise RuntimeError('Unresolved case did not replay identically')
                        row['unresolved_replayed'] = True
                    rows.append(row)
                cells.append({'scenario': scenario, 'strategy': strategy, 'use_ram': use_ram,
                              'policies': [asdict(policy) for policy in policies],
                              'policy_types': [policy_type(policy) for policy in policies],
                              'summary': summarize(rows), 'records': rows})
                print(f'{scenario}/{strategy}/ram={use_ram}: {len(rows)} starts processed; '
                      'completed duels audited, unresolved prefixes replayed', flush=True)
    after = sources(all_policies)
    require_unchanged_sources(before, after)
    if source_commit(before) != commit:
        raise RuntimeError('Study source commit changed during execution')
    payload = {'schema': 'blacklight-experimental-ram-crossbones-explore-v1',
               'source_commit': commit, 'source_sha256': before, 'spec': SPEC.relative_to(ROOT).as_posix(),
               'n_per_cell': n, 'matches_preregistration': n == N_PER_CELL,
               'victor_sheet': sheet_record(victor_sheet), 'crossbones_subset': asdict(subset),
               'initial_distance': DISTANCE, 'max_rounds': MAX_ROUNDS, 'self_damage_mode': MODE,
               'cells': cells,
               'limitations': ['exploratory partial official profile, not full Crossbones',
                               'unresolved death-threshold prefixes replayed, not full-duel audits',
                               'paired seeds within scenario do not certify independent confirmation',
                               'one-dimensional field; no Karma, complete Focus powers or multi-target weapons']}
    # Audit the exact JSON-compatible representation, including frozen sets in
    # profile records, before writing any results.
    payload = json.loads(json.dumps(payload, ensure_ascii=False, default=sorted))
    issues = audit_exploration(payload)
    if issues:
        raise RuntimeError(f'Independent exploration accounting audit failed: {issues}')
    require_unchanged_sources(before, sources(all_policies))
    if source_commit(before) != commit:
        raise RuntimeError('Study source commit changed during final audit')
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2, default=sorted) + '\n')
    print('Experimental exploration saved; no global strategy conclusion is implied.', flush=True)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.output)


if __name__ == '__main__':
    main()
