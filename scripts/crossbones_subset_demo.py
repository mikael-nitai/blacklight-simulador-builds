"""Preserve an audited, explicitly incomplete official-character example."""

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
from experimental.crossbones_subset import build_crossbones_subset
from experimental.ranged_powers_duel import RangedPowersPolicy
from experimental.smg_audit import audit_submachine_duel
from experimental.smg_duel import SubmachineDuel
from scripts.current_study_dev import ROOT, source_commit
from scripts.double_tap_demo import EXTRA as DOUBLE_TAP_SOURCES

SEED = 30
VICTOR = ROOT / 'characters/victor_halle/rank3_2026-10-27_split_fast.json'
EVIDENCE = ROOT / 'character_evidence/crossbones_core_p155.json'
EXTRA = tuple(sorted(set(DOUBLE_TAP_SOURCES + (
    'experimental/crossbones_subset.py', 'experimental/ranged_powers_duel.py',
    'experimental/ranged_powers_audit.py', 'experimental/slow_motion_dodge.py',
    'experimental/slow_motion_duel.py', 'experimental/smg_duel.py',
    'experimental/smg_audit.py', 'character_evidence/crossbones_core_p155.json',
    'CROSSBONES_SUBSET_EXPERIMENT.md', 'RANGED_POWERS_EXPERIMENT.md',
    'scripts/double_tap_demo.py', 'scripts/crossbones_subset_demo.py',
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
    subset = build_crossbones_subset(evidence, accept_incomplete=True)
    victor_sheet = load_sheet(VICTOR)
    profiles = (subset.profile, compile_duel(victor_sheet))
    policies = (RangedPowersPolicy('crossbones parcial', use_ram=False),
                RangedPowersPolicy('victor', weapon='hammer', offhand='blade',
                                   prefer_fast=True, effect_limb=1, use_ram=False))
    before = sources(policies)
    commit = source_commit(before)
    weapons = (subset.ranged_weapon, 'generic')
    battle = SubmachineDuel(profiles, policies, seed=SEED, initial_prone=(False, False),
                            initial_distance=2, max_rounds=6, audit=True,
                            action_registry=DEFAULT_ACTIONS, ranged_weapons=weapons)
    result = battle.run()
    issues = audit_submachine_duel(result, profiles, initial_prone=(False, False),
                                   initial_distance=2, expected_seed=SEED, max_rounds=6,
                                   ruleset=battle.table_ruleset, ranged_weapons=weapons)
    if issues:
        raise RuntimeError(f'Experimental duel audit failed: {issues}')
    if (not any(e['type'] == 'double_tap_end' and e['bleeding'] for e in result.log)
            or not any(e['type'] == 'smg_close_check' for e in result.log)
            or not any(e['type'] == 'fast_use_start' and e['actor'] == profiles[1].name
                       for e in result.log)):
        raise RuntimeError('Selected example did not exercise all declared interactions')
    require_unchanged_sources(before, sources(policies))
    if source_commit(before) != commit:
        raise RuntimeError('Example source commit changed')
    payload = {
        'schema': 'blacklight-experimental-crossbones-subset-demo-v1',
        'source_commit': commit, 'source_sha256': before, 'seed': SEED,
        'crossbones_subset': asdict(subset), 'victor_sheet': sheet_record(victor_sheet),
        'profiles': [asdict(profile) for profile in profiles],
        'policies': [asdict(policy) for policy in policies], 'ranged_weapons': list(weapons),
        'initial_distance': 2, 'initial_prone': [False, False], 'max_rounds': 6,
        'ruleset': battle.table_ruleset, 'result': asdict(result), 'audit_issues': issues,
        'limitations': ['one selected duel; not a statistical or strategy comparison',
                        'Crossbones is an explicitly incomplete subset, not the full official character',
                        'Ram disabled by both policies; other unmodeled powers remain absent'],
    }
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2, default=sorted) + '\n')
    print('Audited incomplete Crossbones example saved; no statistical conclusion is implied.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
