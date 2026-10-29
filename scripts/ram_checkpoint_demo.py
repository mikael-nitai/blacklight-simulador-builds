"""Create one versioned, audited Victor Ram checkpoint, not a full duel."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.sheets import sheet_record
from experimental.ram_checkpoint_audit import audit_ram_checkpoint
from experimental.ram_checkpoint_duel import RamCheckpointDuel
from scripts.current_study_dev import INPUTS, ROOT, declared_sources, source_commit
from scripts.current_study_holdout import holdout_configurations

SEED = 987654
EXTRA = ('experimental/__init__.py', 'experimental/ram_trigger.py', 'experimental/ram_opportunity_duel.py',
         'experimental/ram_opportunity_audit.py', 'experimental/ram_checkpoint_duel.py',
         'experimental/ram_checkpoint_audit.py', 'experimental/ram_transaction.py',
         'experimental/ram_impact.py', 'experimental/ram_record.py',
         'experimental/ram_record_audit.py', 'experimental/ram_rolled.py',
         'scripts/current_study_holdout.py', 'scripts/current_study_confirm.py',
         'scripts/current_study_select.py', 'scripts/current_study_analysis.py',
         'scripts/ram_checkpoint_demo.py', 'RAM_RULING.md', 'RAM_IMPACT_EXPERIMENT.md',
         'RAM_CHECKPOINT_EXPERIMENT.md')


def sources(policies, input_bytes):
    result = declared_sources(policies, None, input_bytes)
    result.update({name: sha256((ROOT / name).read_bytes()).hexdigest() for name in EXTRA})
    return result


def run(output):
    path = Path(output)
    if path.resolve().is_relative_to((ROOT / 'results').resolve()):
        raise ValueError('Experimental checkpoints must not enter the certified results inventory')
    require_new_output(path)
    inputs = tuple(p.read_bytes() for p in INPUTS)
    hero, policies, scenarios = holdout_configurations(inputs)
    foe, foe_policy, distance, board = scenarios['gunner_open']
    if board is not None:
        raise ValueError('This checkpoint supports only the preregistered open-field scenario')
    choices = (policies['hammer_fast_hammer'], foe_policy)
    before = sources(choices, inputs)
    commit = source_commit(before)
    profiles = (compile_duel(hero), compile_duel(foe))
    duel = RamCheckpointDuel(profiles, choices, seed=SEED, initial_distance=distance,
                             max_rounds=30, audit=True, action_registry=DEFAULT_ACTIONS, ram_actor=0)
    checkpoint = duel.run_to_opportunity()
    if checkpoint['status'] != 'opportunity':
        raise RuntimeError('The fixed demonstration did not reach the expected opportunity')
    resolved = duel.resolve_bare_ram()
    issues = audit_ram_checkpoint(resolved['log'], profiles, initial_distance=distance,
                                  ruleset=duel.table_ruleset, seed=SEED)
    if issues:
        raise RuntimeError(f'Checkpoint audit failed: {issues}')
    after = sources(choices, tuple(p.read_bytes() for p in INPUTS))
    require_unchanged_sources(before, after)
    if source_commit(before) != commit:
        raise RuntimeError('Checkpoint source commit changed')
    payload = {'schema': 'blacklight-experimental-ram-checkpoint-demo-v1',
               'source_commit': commit, 'source_sha256': before, 'seed': SEED,
               'sheets': [sheet_record(hero), sheet_record(foe)],
               'policies': [asdict(policy) for policy in choices],
               'initial_distance': distance, 'ruleset': duel.table_ruleset,
               'status': resolved['status'], 'log': resolved['log'], 'audit_issues': issues,
               'limitations': ['one bare Ram checkpoint, not a completed duel or win-rate study',
                               'no Shield or Riposte interaction at the checkpoint',
                               'simultaneous impact hypothesis; Prone continuation not implemented']}
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    print('Experimental Ram checkpoint saved; this is not a full duel.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.output)


if __name__ == '__main__':
    main()
