"""Preserve one independently audited Victor duel; not a statistical study."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.engine import Profile
from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.runner import _source_manifest
from combatants.sheets import load_sheet, sheet_record
from experimental.double_tap_audit import audit_double_tap_duel
from experimental.double_tap_duel import DoubleTapDuel, DoubleTapPolicy
from scripts.current_study_dev import ROOT, source_commit
from scripts.nonlethal_demo import EXTRA as NONLETHAL_SOURCES

SEED = 7
VICTOR = ROOT / 'characters/victor_halle/rank3_2026-10-27_split_fast.json'
EXTRA = tuple(sorted(set(NONLETHAL_SOURCES + (
    'experimental/double_tap_duel.py', 'experimental/double_tap_audit.py',
    'scripts/double_tap_demo.py', 'scripts/verify_sources.py',
    'DOUBLE_TAP_EXPERIMENT.md', 'characters/victor_halle/rank3_2026-10-27_split_fast.json',
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
    sheet = load_sheet(VICTOR)
    shooter = Profile('Atirador sintético', 3, 300, 90, 4, 5, 3, 2, 14, 15, 6,
                      ranged_range=10, ranged_bonus=2, ranged_is_ammunition=True,
                      powers=frozenset({'accuracy', 'double_tap'}))
    profiles = (shooter, compile_duel(sheet))
    policies = (DoubleTapPolicy('atirador', use_ram=False),
                DoubleTapPolicy('victor', weapon='hammer', offhand='blade', prefer_fast=True,
                                effect_limb=1, use_ram=False, shield_react=False))
    before = sources(policies)
    commit = source_commit(before)
    battle = DoubleTapDuel(profiles, policies, initial_prone=(False, False), seed=SEED,
                           initial_distance=2, max_rounds=8, audit=True,
                           action_registry=DEFAULT_ACTIONS)
    result = battle.run()
    issues = audit_double_tap_duel(result, profiles, initial_prone=(False, False),
                                   initial_distance=2, expected_seed=SEED, max_rounds=8,
                                   ruleset=battle.table_ruleset)
    if issues:
        raise RuntimeError(f'Experimental duel audit failed: {issues}')
    types = {event['type'] for event in result.log}
    if not {'double_tap_start', 'double_tap_end', 'fast_use_start'} <= types:
        raise RuntimeError('Demonstration failed to exercise its intended mechanics')
    if not any(event['type'] == 'condition_start' and 'CORE-P95-DOUBLE-TAP' in event['rules']
               for event in result.log):
        raise RuntimeError('Demonstration did not exercise Double Tap bleeding')
    require_unchanged_sources(before, sources(policies))
    if source_commit(before) != commit:
        raise RuntimeError('Demonstration source commit changed')
    payload = {'schema': 'blacklight-experimental-double-tap-demo-v1', 'source_commit': commit,
               'source_sha256': before, 'seed': SEED, 'victor_sheet': sheet_record(sheet),
               'profiles': [asdict(profile) for profile in profiles],
               'policies': [asdict(policy) for policy in policies],
               'initial_distance': 2, 'initial_prone': [False, False], 'max_rounds': 8,
               'ruleset': battle.table_ruleset, 'result': asdict(result), 'audit_issues': issues,
               'limitations': ['one selected illustrative duel, not an efficacy estimate',
                               'the opponent is synthetic, not the full official Crossbones profile',
                               'Ram disabled by both policies; other unmodeled powers remain absent']}
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2, default=sorted) + '\n')
    print('Audited Double Tap demonstration saved; no statistical conclusion is implied.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
