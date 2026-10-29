"""Create one audited experimental Prone duel; not an efficacy study."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.audit import audit_profiled_log
from blacklight.result_audit import audit_battle_result
from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from blacklight.spatial_audit import audit_open_field_distance
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.sheets import sheet_record
from experimental.prone_duel import ProneDuel, PronePolicy
from experimental.prone_duel_audit import audit_prone_log
from scripts.current_study_dev import INPUTS, ROOT, configurations, declared_sources, source_commit

SEED = 246810
INITIAL_PRONE = (False, True)
MAX_ROUNDS = 30
EXTRA = ('experimental/__init__.py', 'experimental/prone.py', 'experimental/prone_duel.py',
         'experimental/prone_duel_audit.py', 'scripts/prone_duel_demo.py', 'PRONE_EXPERIMENT.md')


def sources(policies, input_bytes):
    result = declared_sources(policies, None, input_bytes)
    result.update({name: sha256((ROOT / name).read_bytes()).hexdigest() for name in EXTRA})
    return result


def run(output):
    path = Path(output)
    if path.resolve().is_relative_to((ROOT / 'results').resolve()):
        raise ValueError('Experimental duels must not enter the certified results inventory')
    require_new_output(path)
    inputs = tuple(p.read_bytes() for p in INPUTS)
    hero, choices, scenarios = configurations(inputs)
    foe, base_foe_policy, distance, board = scenarios['mirror']
    if board is not None:
        raise ValueError('This demonstration requires open-field duel geometry')
    policies = (PronePolicy(**asdict(choices['hammer_fast_hammer']), stand_when_prone=True),
                PronePolicy(**asdict(base_foe_policy), stand_when_prone=False))
    profiles = (compile_duel(hero), compile_duel(foe))
    before = sources(policies, inputs)
    commit = source_commit(before)
    duel = ProneDuel(profiles, policies, initial_prone=INITIAL_PRONE, seed=SEED,
                     initial_distance=distance, max_rounds=MAX_ROUNDS, audit=True,
                     action_registry=DEFAULT_ACTIONS)
    result = duel.run()
    issues = audit_profiled_log(result.log, profiles, ruleset=duel.table_ruleset)
    issues += audit_battle_result(result, profiles, expected_seed=SEED, max_rounds=MAX_ROUNDS)
    issues += audit_open_field_distance(result.log, distance)
    issues += audit_prone_log(result.log, profiles, initial_prone=INITIAL_PRONE,
                              initial_distance=distance, stack_stunned_edge=duel.stack_stunned_edge)
    if issues:
        raise RuntimeError(f'Experimental Prone duel audit failed: {issues}')
    after = sources(policies, tuple(p.read_bytes() for p in INPUTS))
    require_unchanged_sources(before, after)
    if source_commit(before) != commit:
        raise RuntimeError('Experimental Prone source commit changed')
    payload = {'schema': 'blacklight-experimental-prone-duel-demo-v1',
               'source_commit': commit, 'source_sha256': before, 'seed': SEED,
               'sheets': [sheet_record(hero), sheet_record(foe)],
               'policies': [asdict(policy) for policy in policies],
               'initial_distance': distance, 'initial_prone': list(INITIAL_PRONE),
               'ruleset': duel.table_ruleset, 'result': asdict(result), 'audit_issues': issues,
               'limitations': ['single illustrative experimental duel, not an efficacy study',
                               'synthetic mirror deliberately stays prone; not an optimal opponent',
                               'Ram, crawling and complex terrain are not implemented']}
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print('Experimental Prone duel saved; no efficacy conclusion is implied.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.output)


if __name__ == '__main__':
    main()
