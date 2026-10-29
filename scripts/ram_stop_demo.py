"""Preserve a synthetic boundary example of the current Ram table ruling."""

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
from scripts.ram_incapacity_demo import EXTRA as INCAPACITY_SOURCES

MODE = 'stop_before_heal_reject_lethal'
SEED = 1
EXTRA = tuple(sorted(set(INCAPACITY_SOURCES + ('experimental/ram_stop_audit.py',
              'scripts/ram_stop_demo.py', 'RAM_RULING.md'))))


class StationaryPolicy(RamPronePolicy):
    def choose_move(self, observation):
        return Move()


def sources(policies):
    source = _source_manifest(policies, None)
    source.update({name: sha256((ROOT / name).read_bytes()).hexdigest() for name in EXTRA})
    return source


def run(output):
    path = Path(output)
    if path.resolve().is_relative_to((ROOT / 'results').resolve()):
        raise ValueError('Experimental examples must not enter the certified results inventory')
    require_new_output(path)
    attacker = Profile('Atacante sintético', 3, 20, 60, 4, 0, 5, 2, 14, 10, 5,
                       initiative_modifier=100, powers=frozenset({'healing_factor'}))
    target = Profile('Alvo sintético', 3, 250, 60, 2, 0, 5, 2, 12, 10, 5,
                     initiative_modifier=0)
    profiles = (attacker, target)
    policies = (RamPronePolicy('atacante'), StationaryPolicy('alvo', always_wait=True, use_ram=False))
    before = sources(policies)
    commit = source_commit(before)
    duel = RamIncapacityDuel(profiles, policies, self_damage_mode=MODE,
                             stop_on_attacker=attacker.name, initial_prone=(False, False),
                             seed=SEED, initial_distance=10, max_rounds=1, audit=True,
                             action_registry=DEFAULT_ACTIONS)
    result = duel.run()
    issues = audit_nonlethal_ram_duel(result, profiles, self_damage_mode=MODE,
                stop_on_attacker=attacker.name, initial_prone=(False, False), initial_distance=10,
                expected_seed=SEED, max_rounds=1, ruleset=duel.table_ruleset)
    if issues:
        raise RuntimeError(f'Ram ruling example failed audit: {issues}')
    if (result.final_health != (-1, 210) or result.outcome != 'win'
            or not any(event['type'] == 'ram_incapacity_stop' for event in result.log)):
        raise RuntimeError('The selected example did not reach the intended boundary')
    require_unchanged_sources(before, sources(policies))
    if source_commit(before) != commit:
        raise RuntimeError('Example source commit changed')
    payload = {'schema': 'blacklight-experimental-ram-stop-demo-v1', 'source_commit': commit,
               'source_sha256': before, 'seed': SEED, 'mode': MODE, 'stop_on_attacker': attacker.name,
               'profiles': [asdict(profile) for profile in profiles],
               'policies': [asdict(policy) for policy in policies],
               'initial_prone': [False, False], 'initial_distance': 10, 'max_rounds': 1,
               'ruleset': duel.table_ruleset, 'result': asdict(result), 'audit_issues': issues,
               'limitations': ['synthetic boundary case, not Victor or an efficacy study',
                               'self-damage reaching death threshold aborts because the table has not decided']}
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2, default=sorted) + '\n')
    print('Audited Ram stop example saved; no statistical conclusion is implied.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
