"""Create one audited full Victor duel with experimental bare Ram and Prone."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.sheets import sheet_record
from experimental.ram_prone_audit import audit_ram_prone_duel
from experimental.ram_prone_duel import RamProneDuel, RamPronePolicy
from scripts.current_study_dev import INPUTS, ROOT, declared_sources, source_commit
from scripts.current_study_holdout import holdout_configurations

SEED = 987654
INITIAL_PRONE = (False, False)
MAX_ROUNDS = 30
EXTRA = ('experimental/__init__.py', 'experimental/prone.py', 'experimental/prone_duel.py',
         'experimental/prone_duel_audit.py', 'experimental/incapacity_endturn_audit.py',
         'experimental/ram_prone_duel.py',
         'experimental/ram_prone_audit.py', 'experimental/ram_opportunity_duel.py',
         'experimental/ram_opportunity_audit.py', 'experimental/ram_trigger.py',
         'experimental/ram_transaction.py', 'experimental/ram_impact.py',
         'experimental/ram_record.py', 'experimental/ram_record_audit.py',
         'experimental/ram_rolled.py', 'scripts/current_study_holdout.py',
         'scripts/current_study_confirm.py', 'scripts/current_study_select.py',
         'scripts/current_study_analysis.py', 'scripts/ram_prone_demo.py',
         'RAM_RULING.md', 'PRONE_EXPERIMENT.md', 'RAM_PRONE_EXPERIMENT.md')


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
    hero, choices, scenarios = holdout_configurations(inputs)
    foe, foe_policy, distance, board = scenarios['gunner_open']
    if board is not None:
        raise ValueError('The demonstration needs the open-field scenario')
    policies = (RamPronePolicy(**asdict(choices['hammer_fast_hammer']), use_ram=True),
                RamPronePolicy(**asdict(foe_policy), use_ram=False))
    profiles = (compile_duel(hero), compile_duel(foe))
    before = sources(policies, inputs)
    commit = source_commit(before)
    duel = RamProneDuel(profiles, policies, initial_prone=INITIAL_PRONE, seed=SEED,
                        initial_distance=distance, max_rounds=MAX_ROUNDS, audit=True,
                        action_registry=DEFAULT_ACTIONS)
    result = duel.run()
    issues = audit_ram_prone_duel(result, profiles, initial_prone=INITIAL_PRONE,
                                  initial_distance=distance, expected_seed=SEED,
                                  max_rounds=MAX_ROUNDS, ruleset=duel.table_ruleset,
                                  stack_stunned_edge=duel.stack_stunned_edge)
    if issues:
        raise RuntimeError(f'Experimental Ram/Prone duel audit failed: {issues}')
    after = sources(policies, tuple(p.read_bytes() for p in INPUTS))
    require_unchanged_sources(before, after)
    if source_commit(before) != commit:
        raise RuntimeError('Experimental duel source commit changed')
    payload = {'schema': 'blacklight-experimental-ram-prone-duel-demo-v1',
               'source_commit': commit, 'source_sha256': before, 'seed': SEED,
               'sheets': [sheet_record(hero), sheet_record(foe)],
               'policies': [asdict(policy) for policy in policies],
               'initial_distance': distance, 'initial_prone': list(INITIAL_PRONE),
               'ruleset': duel.table_ruleset, 'max_rounds': MAX_ROUNDS,
               'result': asdict(result), 'audit_issues': issues,
               'limitations': ['one illustrative experimental duel, not an efficacy study',
                               'bare Ram only; attacker retains active Shield and declines Ram',
                               'self-incapacitating Ram aborts; no complex terrain, Karma or Focus attacks']}
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print('Experimental full Ram/Prone duel saved; no efficacy conclusion is implied.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.output)


if __name__ == '__main__':
    main()
