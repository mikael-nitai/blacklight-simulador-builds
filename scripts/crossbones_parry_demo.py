"""Save an audited duel using the expanded, incomplete Crossbones subset."""

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
from experimental.crossbones_subset import build_crossbones_parry_subset
from experimental.parry_audit import audit_parry_duel
from experimental.parry_duel import ParryDuel, ParryPolicy
from scripts.crossbones_subset_demo import EXTRA as SUBSET_SOURCES, EVIDENCE, VICTOR
from scripts.current_study_dev import ROOT, source_commit

SEED = 115
EXTRA = tuple(sorted(set(SUBSET_SOURCES + (
    'experimental/parry_duel.py', 'experimental/parry_audit.py',
    'experimental/point_blank_parry.py', 'experimental/reaction_pools.py',
    'FAST_HANDS_PARRY_EXPERIMENT.md', 'scripts/crossbones_parry_demo.py',
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
    subset = build_crossbones_parry_subset(evidence, accept_incomplete=True)
    victor_sheet = load_sheet(VICTOR)
    profiles = (subset.profile, compile_duel(victor_sheet))
    policies = (ParryPolicy('crossbones parcial', use_ram=False),
                ParryPolicy('victor', weapon='hammer', offhand='blade', prefer_fast=True,
                            effect_limb=1, use_ram=False, shield_react=True))
    before = sources(policies)
    commit = source_commit(before)
    weapons = (subset.ranged_weapon, 'generic')
    duel = ParryDuel(profiles, policies, seed=SEED, initial_prone=(False, False),
                     initial_distance=1, max_rounds=8, audit=True,
                     action_registry=DEFAULT_ACTIONS, ranged_weapons=weapons)
    result = duel.run()
    issues = audit_parry_duel(result, profiles, initial_prone=(False, False), initial_distance=1,
                              expected_seed=SEED, max_rounds=8, ruleset=duel.table_ruleset,
                              ranged_weapons=weapons)
    if issues:
        raise RuntimeError(f'Experimental parry duel failed audit: {issues}')
    if not any(event['type'] == 'parry_start' for event in result.log):
        raise RuntimeError('Selected example did not exercise Point-Blank Parry')
    require_unchanged_sources(before, sources(policies))
    if source_commit(before) != commit:
        raise RuntimeError('Example source commit changed')
    payload = {
        'schema': 'blacklight-experimental-crossbones-parry-demo-v1',
        'source_commit': commit, 'source_sha256': before, 'seed': SEED,
        'crossbones_subset': asdict(subset), 'victor_sheet': sheet_record(victor_sheet),
        'profiles': [asdict(profile) for profile in profiles],
        'policies': [asdict(policy) for policy in policies], 'ranged_weapons': list(weapons),
        'initial_distance': 1, 'initial_prone': [False, False], 'max_rounds': 8,
        'ruleset': duel.table_ruleset, 'result': asdict(result), 'audit_issues': issues,
        'limitations': ['one selected example, not a statistical or strategy comparison',
                        'Crossbones is incomplete; omitted features are listed in the subset',
                        'Ram is disabled; its incapacitation boundary is not modeled by this host'],
    }
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2, default=sorted) + '\n')
    print('Audited partial Crossbones parry example saved; no statistical conclusion is implied.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
