"""Compare explicit Ram self-incapacity hypotheses on one synthetic seed."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.engine import Move, Profile
from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.actions import DEFAULT_ACTIONS
from combatants.runner import _source_manifest
from experimental.nonlethal_ram_audit import audit_nonlethal_ram_duel
from experimental.ram_incapacity_duel import RamIncapacityDuel
from experimental.ram_prone_duel import RamPronePolicy
from scripts.current_study_dev import ROOT, source_commit

SEED = 1
MODES = ('lethal_impact', 'nonlethal_impact')
EXTRA = ('experimental/__init__.py', 'experimental/prone.py', 'experimental/prone_duel.py',
         'experimental/prone_duel_audit.py', 'experimental/incapacity_endturn_audit.py',
         'experimental/ram_prone_duel.py',
         'experimental/ram_prone_audit.py', 'experimental/ram_stop_audit.py', 'experimental/ram_opportunity_duel.py',
         'experimental/ram_opportunity_audit.py', 'experimental/ram_trigger.py',
         'experimental/ram_transaction.py', 'experimental/ram_impact.py',
         'experimental/ram_record.py', 'experimental/ram_record_audit.py',
         'experimental/ram_rolled.py', 'experimental/nonlethal_ram_duel.py',
         'experimental/nonlethal_ram_audit.py', 'experimental/ram_incapacity_duel.py',
         'scripts/current_study_dev.py', 'scripts/ram_incapacity_demo.py',
         'RAM_RULING.md', 'RAM_INCAPACITY_EXPERIMENT.md', 'NONLETHAL_EXPERIMENT.md')


class PassivePolicy(RamPronePolicy):
    def choose_move(self, observation):
        return Move()


def sources(policies):
    result = _source_manifest(policies, None)
    result.update({name: sha256((ROOT / name).read_bytes()).hexdigest() for name in EXTRA})
    return result


def run(output):
    path = Path(output)
    if path.resolve().is_relative_to((ROOT / 'results').resolve()):
        raise ValueError('Experimental comparisons must not enter the certified results inventory')
    require_new_output(path)
    profiles = (Profile('Attacker', 3, 1, 60, 4, 0, 5, 2, 14, 10, 5,
                        initiative_modifier=100, powers=frozenset({'healing_factor'})),
                Profile('Target', 3, 1, 60, 2, 0, 5, 2, 12, 10, 5, initiative_modifier=0))
    policies = (RamPronePolicy('attacker'), PassivePolicy('target', always_wait=True, use_ram=False))
    before = sources(policies)
    commit = source_commit(before)
    results = {}
    for mode in MODES:
        duel = RamIncapacityDuel(profiles, policies, self_damage_mode=mode,
                                 initial_prone=(False, False), seed=SEED, initial_distance=10,
                                 max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
        result = duel.run()
        issues = audit_nonlethal_ram_duel(result, profiles, initial_prone=(False, False),
                                          initial_distance=10, expected_seed=SEED, max_rounds=1,
                                          ruleset=duel.table_ruleset, self_damage_mode=mode)
        if issues:
            raise RuntimeError(f'{mode}: experimental audit failed: {issues}')
        results[mode] = asdict(result)
    attacks = [next(event for event in results[mode]['log'] if event['type'] == 'ram_attack') for mode in MODES]
    first, second = (event['transaction']['parameters'] for event in attacks)
    if (first['target_faces'] != second['target_faces'] or first['attacker_faces'] != second['attacker_faces']
            or results['lethal_impact']['outcome'] != 'draw'
            or results['nonlethal_impact']['winner'] != 'Attacker'):
        raise RuntimeError('Fixed demonstration did not exercise the intended hypothesis contrast')
    require_unchanged_sources(before, sources(policies))
    if source_commit(before) != commit:
        raise RuntimeError('Experimental sensitivity source commit changed')
    payload = {'schema': 'blacklight-experimental-ram-incapacity-demo-v1',
               'seed': SEED, 'source_commit': commit, 'source_sha256': before,
               'profiles': [asdict(profile) for profile in profiles],
               'policies': [asdict(policy) for policy in policies],
               'initial_distance': 10, 'initial_prone': [False, False], 'max_rounds': 1,
               'results': results,
               'limitations': ['hypothetical, not a table ruling or efficacy study',
                               'one seed in a synthetic boundary case, not Victor or an official NPC',
                               'automatic healing of a living unconscious attacker is assumed']}
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2, default=sorted) + '\n')
    print('Experimental self-incapacity sensitivity example saved; no table ruling is implied.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
