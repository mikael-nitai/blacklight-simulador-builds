"""Save an audited Ram/Stopping/Parry duel with an incomplete official subset."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.runner import _source_manifest
from combatants.sheets import load_sheet, sheet_record
from experimental.crossbones_subset import build_crossbones_stopping_subset
from experimental.stopping_audit import audit_stopping_duel
from experimental.stopping_duel import StoppingPolicy
from experimental.stopping_ram_duel import StoppingRamDuel
from scripts.crossbones_stopping_demo import EXTRA as STOPPING_SOURCES
from scripts.crossbones_subset_demo import EVIDENCE, VICTOR
from scripts.current_study_dev import ROOT, source_commit

SEED = 45
MODE = 'stop_before_heal_reject_lethal'
EXTRA = tuple(sorted(set(STOPPING_SOURCES + (
    'experimental/ram_incapacity_duel.py', 'experimental/incapacity_endturn_audit.py',
    'experimental/ram_stop_audit.py', 'experimental/stopping_ram_duel.py',
    'RAM_INCAPACITY_EXPERIMENT.md', 'scripts/crossbones_ram_demo.py',
))))


def sources(policies):
    source = _source_manifest(policies, None)
    source.update({name: sha256((ROOT / name).read_bytes()).hexdigest() for name in EXTRA})
    return source


def run(output):
    path = Path(output)
    if path.resolve().is_relative_to((ROOT / 'results').resolve()):
        raise ValueError('Experimental results must not enter the certified results inventory')
    require_new_output(path)
    evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
    subset = build_crossbones_stopping_subset(evidence, accept_incomplete=True)
    victor_sheet = load_sheet(VICTOR)
    profiles = (subset.profile, compile_duel(victor_sheet))
    policies = (StoppingPolicy('crossbones parcial', prefer_stopping=True, use_ram=False),
                StoppingPolicy('victor', weapon='hammer', offhand='blade', prefer_fast=True,
                               effect_limb=1, use_ram=True, shield_react=True))
    before = sources(policies)
    commit = source_commit(before)
    weapons = (subset.ranged_weapon, 'generic')
    duel = StoppingRamDuel(profiles, policies, seed=SEED, initial_prone=(False, False),
                           initial_distance=10, max_rounds=8, audit=True,
                           action_registry=DEFAULT_ACTIONS, ranged_weapons=weapons,
                           stop_on_attacker=profiles[1].name)
    result = duel.run()
    issues = audit_stopping_duel(result, profiles, initial_prone=(False, False), initial_distance=10,
                                 expected_seed=SEED, max_rounds=8, ruleset=duel.table_ruleset,
                                 ranged_weapons=weapons, self_damage_mode=MODE,
                                 stop_on_attacker=profiles[1].name)
    if issues:
        raise RuntimeError(f'Experimental Ram and ranged powers duel failed audit: {issues}')
    missed = {event['trigger'] for event in result.log if event['type'] == 'ram_attack'
              and not event['transaction']['parameters']['success']}
    if (not any(event['type'] == 'parry_start' and event['source_trigger'] in missed for event in result.log)
            or not any(event['type'] == 'stopping_start' for event in result.log)):
        raise RuntimeError('Selected example did not exercise Ram, Parry and Stopping Power')
    require_unchanged_sources(before, sources(policies))
    if source_commit(before) != commit:
        raise RuntimeError('Example source commit changed')
    payload = {
        'schema': 'blacklight-experimental-crossbones-ram-demo-v1',
        'source_commit': commit, 'source_sha256': before, 'seed': SEED,
        'crossbones_subset': asdict(subset), 'victor_sheet': sheet_record(victor_sheet),
        'profiles': [asdict(profile) for profile in profiles],
        'policies': [asdict(policy) for policy in policies], 'ranged_weapons': list(weapons),
        'initial_distance': 10, 'initial_prone': [False, False], 'max_rounds': 8,
        'ruleset': duel.table_ruleset, 'self_damage_mode': MODE,
        'stop_on_attacker': profiles[1].name, 'result': asdict(result), 'audit_issues': issues,
        'limitations': ['one selected example, not a statistical or strategy comparison',
                        'Crossbones is incomplete; omitted features are listed in the subset',
                        'Ram self-damage reaching death threshold aborts because it is undecided'],
    }
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2, default=sorted) + '\n')
    print('Audited partial Crossbones and Ram example saved; no statistical conclusion is implied.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
