"""Run a preregistered exploratory comparison of escape and attacking."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
import platform
from pathlib import Path

from blacklight.experiment import wilson
from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.runner import _source_manifest
from combatants.sheets import load_sheet, sheet_record
from experimental.crossbones_reactive_grapple_subset import build_crossbones_reactive_grapple_subset
from experimental.entangled_reaction_audit import audit_entangled_reactions
from experimental.entangled_reaction_duel import EntangledReactionDuel, EntangledReactionPolicy
from scripts.crossbones_ram_demo import EVIDENCE, VICTOR
from scripts.current_study_dev import ROOT, source_commit
from scripts.entangled_reaction_demo import EXTRA as PRIOR_SOURCES
from scripts.audit_grapple_strategy_explore import audit

N = 1000
LIMIT = 30
EXTRA = tuple(sorted(set(PRIOR_SOURCES + ('GRAPPLE_STRATEGY_EXPLORATION_SPEC.md',
    'scripts/grapple_strategy_explore.py', 'scripts/audit_grapple_strategy_explore.py',
    'scripts/replay_grapple_strategy_explore.py', 'experimental/crossbones_reactive_grapple_subset.py',
    'scripts/audit_ram_crossbones_explore.py', 'scripts/verify_sources.py', 'scripts/current_study_dev.py'))))


def seed_for(index):
    if type(index) is not int or not 0 <= index < N:
        raise ValueError('Invalid preregistered seed index')
    return int.from_bytes(sha256(f'blacklight-grapple-explore-v1:{index}'.encode()).digest()[:8], 'big')


def policies_for(strategy):
    if strategy not in ('escape', 'attack'):
        raise ValueError('Unknown Victor policy')
    foe = EntangledReactionPolicy('crossbones_grapple', prefer_grapple=True, prefer_stopping=True,
                                  use_ram=False, treat_bleeding=True, attack_when_grabbing=True)
    hero = EntangledReactionPolicy('victor_' + strategy, weapon='hammer', offhand='blade',
            prefer_fast=True, effect_limb=0, shield_react=True, knockback_stance=False,
            use_ram=False, escape_reaction=strategy == 'escape', attack_when_grabbed=strategy == 'attack')
    return foe, hero


def sources(policies):
    result = _source_manifest(policies, None)
    result.update({name: sha256((ROOT / name).read_bytes()).hexdigest() for name in EXTRA})
    return result


def digest(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=sorted)
    return sha256(raw.encode('utf-8')).hexdigest()


def simulate(profiles, policies, ranged_weapon, seed, *, inside_attack_trouble, trigger_mode):
    weapons = (ranged_weapon, 'generic')
    duel = EntangledReactionDuel(profiles, policies, seed=seed, initial_prone=(False, False),
        initial_distance=1, max_rounds=LIMIT, audit=True, action_registry=DEFAULT_ACTIONS,
        ranged_weapons=weapons, stop_on_attacker=profiles[1].name,
        declared_armed_lethal=(profiles[0].name,), escape_trigger_mode=trigger_mode,
        inside_attack_trouble=inside_attack_trouble)
    result = duel.run()
    issues = audit_entangled_reactions(result, profiles, inside_attack_trouble=inside_attack_trouble,
        declared_armed_lethal=(profiles[0].name,), escape_trigger_mode=trigger_mode,
        ranged_weapons=weapons, initial_prone=(False, False), initial_distance=1,
        expected_seed=seed, max_rounds=LIMIT, ruleset=duel.table_ruleset,
        self_damage_mode='stop_before_heal_reject_lethal', stop_on_attacker=profiles[1].name)
    if issues:
        raise RuntimeError(f'Duel {seed} failed its independent audit: {issues}')
    if result.outcome == 'win' and result.winner in (profiles[0].name, profiles[1].name):
        status = 'victory' if result.winner == profiles[1].name else 'defeat'
    elif result.outcome in ('draw', 'inconclusive') and result.winner is None:
        status = result.outcome
    else:
        raise RuntimeError('Unexpected duel outcome')
    ends = [e for e in result.log if e['type'] == 'grapple_end']
    escapes = [e for e in result.log if e['type'] == 'grapple_escape']
    marker_triggers = {e['trigger'] for e in result.log
                       if e['type'] == 'entangled_attack_check' and e['actor'] == profiles[1].name}
    attacks = [e for e in result.log if e['type'] == 'attack' and e['trigger'] in marker_triggers]
    return {'seed': seed, 'status': status, 'rounds': result.rounds, 'turns': result.turns,
            'final_health': list(result.final_health), 'final_focus': list(result.final_focus),
            'grapple_attempts': len(ends), 'grapple_hits': sum(e['transaction']['attack_success'] for e in ends),
            'grapple_fantastic': sum(e['transaction']['fantastic_success'] for e in ends),
            'reaction_escapes': sum(e['timing'] == 'reaction' for e in escapes),
            'standard_escapes': sum(e['timing'] == 'standard' for e in escapes),
            'held_attacks': len(attacks), 'result_sha256': digest(asdict(result)),
            'audit': 'complete_duel_passed'}


def summarize(rows):
    counts = {s: sum(row['status'] == s for row in rows)
              for s in ('victory', 'defeat', 'draw', 'inconclusive')}
    n = len(rows)
    if n < 1 or sum(counts.values()) != n:
        raise ValueError('Invalid outcomes')
    return {'n': n, 'counts': counts, 'victory_fraction': counts['victory'] / n,
            'victory_wilson_95': list(wilson(counts['victory'], n)),
            'ever_grabbed': sum(row['grapple_hits'] > 0 for row in rows),
            'mean_victor_final_health': sum(row['final_health'][1] for row in rows) / n,
            'mean_victor_final_focus': sum(row['final_focus'][1] for row in rows) / n,
            'grapple_hits': sum(row['grapple_hits'] for row in rows),
            'reaction_escapes': sum(row['reaction_escapes'] for row in rows),
            'standard_escapes': sum(row['standard_escapes'] for row in rows),
            'held_attacks': sum(row['held_attacks'] for row in rows)}


def run(output, *, n=N):
    path = Path(output)
    if path.resolve().is_relative_to((ROOT / 'results').resolve()):
        raise ValueError('Experimental results must not enter the certified inventory')
    if type(n) is not int or not 1 <= n <= N:
        raise ValueError('Invalid sample size')
    require_new_output(path)
    subset = build_crossbones_reactive_grapple_subset(json.loads(EVIDENCE.read_text(encoding='utf-8')),
                                                       accept_incomplete=True)
    sheet = load_sheet(VICTOR)
    profiles = (subset.profile, compile_duel(sheet))
    policies = tuple(policy for strategy in ('escape', 'attack') for policy in policies_for(strategy))
    before = sources(policies)
    commit = source_commit(before)
    if len({seed_for(index) for index in range(n)}) != n:
        raise RuntimeError('Seed collision')
    cells = []
    for strategy in ('escape', 'attack'):
        for trouble in (False, True):
            for mode in ('attack', 'condition'):
                cell_policies = policies_for(strategy)
                rows = [dict(index=i, **simulate(profiles, cell_policies, subset.ranged_weapon, seed_for(i),
                        inside_attack_trouble=trouble, trigger_mode=mode)) for i in range(n)]
                cells.append({'strategy': strategy, 'inside_attack_trouble': trouble, 'trigger_mode': mode,
                              'policies': [asdict(p) for p in cell_policies],
                              'policy_types': [f'{type(p).__module__}.{type(p).__qualname__}'
                                               for p in cell_policies],
                              'summary': summarize(rows), 'records': rows})
                print(f'{strategy}/inside_trouble={trouble}/trigger={mode}: {n} audited starts', flush=True)
    require_unchanged_sources(before, sources(policies))
    if source_commit(before) != commit:
        raise RuntimeError('Sources changed during exploration')
    payload = {'schema': 'blacklight-experimental-grapple-strategy-explore-v1', 'source_commit': commit,
        'source_sha256': before, 'spec': 'GRAPPLE_STRATEGY_EXPLORATION_SPEC.md', 'n_per_cell': n,
        'matches_preregistration': n == N, 'initial_distance': 1, 'max_rounds': LIMIT,
        'runtime': {'python_version': platform.python_version(),
                    'python_implementation': platform.python_implementation()},
        'victor_sheet': sheet_record(sheet), 'crossbones_subset': asdict(subset), 'cells': cells,
        'limitations': ['exploratory incomplete official profile and one-dimensional field',
          'self-hit, third parties, carrying and knockback during holds are not modeled',
          'inside-attack trouble and Escape trigger identity are explicit hypotheses',
          'hold persists when the holder is Stunned; Karma and Ram are not used']}
    payload = json.loads(json.dumps(payload, ensure_ascii=False, default=sorted))
    issues = audit(payload)
    if issues:
        raise RuntimeError(f'Independent exploration audit failed: {issues}')
    require_unchanged_sources(before, sources(policies))
    if source_commit(before) != commit:
        raise RuntimeError('Sources changed during final audit')
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print('Exploratory comparison saved; no universal strategy conclusion is implied.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
