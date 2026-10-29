"""Preserve a verified before/after nonlethal example, not an efficacy study."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.engine import Profile
from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.actions import DEFAULT_ACTIONS
from combatants.runner import _source_manifest
from experimental.nonlethal_ram_audit import audit_nonlethal_ram_duel
from experimental.nonlethal_ram_duel import NonlethalRamProneDuel
from experimental.ram_prone_audit import audit_ram_prone_duel
from experimental.ram_prone_duel import RamProneDuel, RamPronePolicy
from scripts.current_study_dev import ROOT, source_commit

SEED = 1
EXTRA = ('experimental/__init__.py', 'experimental/prone.py', 'experimental/prone_duel.py',
         'experimental/prone_duel_audit.py', 'experimental/incapacity_endturn_audit.py',
         'experimental/ram_prone_duel.py',
         'experimental/ram_prone_audit.py', 'experimental/ram_stop_audit.py', 'experimental/ram_opportunity_duel.py',
         'experimental/ram_opportunity_audit.py', 'experimental/ram_trigger.py',
         'experimental/ram_transaction.py', 'experimental/ram_impact.py',
         'experimental/ram_record.py', 'experimental/ram_record_audit.py',
         'experimental/ram_rolled.py', 'experimental/nonlethal_ram_duel.py',
         'experimental/nonlethal_ram_audit.py', 'scripts/current_study_dev.py',
         'scripts/nonlethal_demo.py', 'NONLETHAL_GAP.md', 'NONLETHAL_EXPERIMENT.md')


def sources(policies):
    result = _source_manifest(policies, None)
    result.update({name: sha256((ROOT / name).read_bytes()).hexdigest() for name in EXTRA})
    return result


def run(output):
    path = Path(output)
    if path.resolve().is_relative_to((ROOT / 'results').resolve()):
        raise ValueError('Experimental comparisons must not enter the certified results inventory')
    require_new_output(path)
    attacker = Profile('Attacker', 3, 100, 60, 4, 0, 5, 2, 14, 10, 5, initiative_modifier=100)
    target = Profile('Target', 3, 1, 60, 2, 0, 5, 2, 12, 10, 5, initiative_modifier=0)
    profiles = (attacker, target)
    policies = (RamPronePolicy('attacker', use_ram=False),
                RamPronePolicy('stationary', always_wait=True, use_ram=False))
    before = sources(policies)
    commit = source_commit(before)
    args = dict(initial_prone=(False, False), seed=SEED, initial_distance=1,
                max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
    original_host = RamProneDuel(profiles, policies, **args)
    corrected_host = NonlethalRamProneDuel(profiles, policies, **args)
    original, corrected = original_host.run(), corrected_host.run()
    context = dict(initial_prone=(False, False), initial_distance=1, expected_seed=SEED,
                   max_rounds=1, ruleset=original_host.table_ruleset)
    issues = audit_ram_prone_duel(original, profiles, **context)
    issues += audit_nonlethal_ram_duel(corrected, profiles, **context)
    if issues:
        raise RuntimeError(f'Nonlethal demonstration audit failed: {issues}')
    if original.final_health[1] >= -target.max_health or corrected.final_health[1] != 0:
        raise RuntimeError('The fixed demonstration did not exercise the expected boundary')
    require_unchanged_sources(before, sources(policies))
    if source_commit(before) != commit:
        raise RuntimeError('Nonlethal demonstration source commit changed')
    payload = {'schema': 'blacklight-experimental-nonlethal-demo-v1', 'seed': SEED,
               'source_commit': commit, 'source_sha256': before,
               'profiles': [asdict(profile) for profile in profiles],
               'policies': [asdict(policy) for policy in policies],
               'initial_distance': 1, 'max_rounds': 1,
               'baseline': asdict(original), 'experimental': asdict(corrected),
               'audit_issues': issues,
               'limitations': ['synthetic boundary example, not Victor or an official NPC',
                               'experimental host; lethal declarations and ambiguous armed cases remain unsupported']}
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2, default=sorted) + '\n')
    print('Audited nonlethal comparison saved; not an efficacy study.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
