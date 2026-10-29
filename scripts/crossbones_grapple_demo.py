"""Save an audited example of a partial Crossbones using Grappling Technique."""

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
from experimental.crossbones_grapple_subset import build_crossbones_grapple_subset
from experimental.grappling_duel import GrapplingDuel, GrapplingPolicy
from experimental.grappling_duel_audit import audit_grappling_duel
from scripts.adaptive_armed_melee_demo import EXTRA as PRIOR_SOURCES
from scripts.crossbones_ram_demo import EVIDENCE, VICTOR
from scripts.current_study_dev import ROOT, source_commit

SEED = 5
EXTRA = tuple(sorted(set(PRIOR_SOURCES + ('GRAPPLING_EXPERIMENT.md',
    'experimental/crossbones_grapple_subset.py', 'experimental/grappling.py',
    'experimental/grappling_audit.py', 'experimental/grappling_duel.py',
    'experimental/grappling_duel_audit.py', 'scripts/crossbones_grapple_demo.py'))))


def sources(policies):
    values = _source_manifest(policies, None)
    values.update({name: sha256((ROOT / name).read_bytes()).hexdigest() for name in EXTRA})
    return values


def run(output):
    path = Path(output)
    if path.resolve().is_relative_to((ROOT / 'results').resolve()):
        raise ValueError('Experimental results must not enter certified results inventory')
    require_new_output(path)
    evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
    subset = build_crossbones_grapple_subset(evidence, accept_incomplete=True)
    sheet = load_sheet(VICTOR)
    profiles = (subset.profile, compile_duel(sheet))
    policies = (GrapplingPolicy('crossbones', prefer_grapple=True, prefer_stopping=True,
                                use_ram=False, treat_bleeding=True, kite=True, move_after_attack=True),
                GrapplingPolicy('victor', weapon='hammer', shield_react=True,
                                use_ram=False, escape_reaction=True))
    weapons = (subset.ranged_weapon, 'generic')
    declared = (profiles[0].name,)
    before = sources(policies)
    commit = source_commit(before)
    duel = GrapplingDuel(profiles, policies, seed=SEED, initial_prone=(False, False),
        initial_distance=1, max_rounds=4, audit=True, action_registry=DEFAULT_ACTIONS,
        ranged_weapons=weapons, stop_on_attacker=profiles[1].name,
        declared_armed_lethal=declared, escape_trigger_mode='condition')
    result = duel.run()
    issues = audit_grappling_duel(result, profiles, declared_armed_lethal=declared,
        escape_trigger_mode='condition', ranged_weapons=weapons, initial_prone=(False, False),
        initial_distance=1, expected_seed=SEED, max_rounds=4, ruleset=duel.table_ruleset,
        self_damage_mode='stop_before_heal_reject_lethal', stop_on_attacker=profiles[1].name)
    if issues:
        raise RuntimeError(f'Grappling duel audit failed: {issues}')
    if not any(e['type'] == 'grapple_escape' and e['timing'] == 'reaction' for e in result.log):
        raise RuntimeError('Selected seed must exercise a reaction Escape')
    require_unchanged_sources(before, sources(policies))
    if source_commit(before) != commit:
        raise RuntimeError('Example source commit changed')
    payload = {'schema': 'blacklight-experimental-crossbones-grapple-demo-v1',
        'source_commit': commit, 'source_sha256': before, 'seed': SEED,
        'crossbones_subset': asdict(subset), 'victor_sheet': sheet_record(sheet),
        'profiles': [asdict(p) for p in profiles], 'policies': [asdict(p) for p in policies],
        'policy_types': [f'{type(p).__module__}.{type(p).__qualname__}' for p in policies],
        'ranged_weapons': weapons, 'declared_armed_lethal': declared, 'escape_trigger_mode': 'condition',
        'initial_distance': 1, 'initial_prone': [False, False], 'max_rounds': 4,
        'ruleset': duel.table_ruleset, 'self_damage_mode': 'stop_before_heal_reject_lethal',
        'stop_on_attacker': profiles[1].name, 'result': asdict(result), 'audit_issues': issues,
        'limitations': ['one selected example, not an efficacy study', 'incomplete official profile',
            'the condition trigger is a hypothesis, not a ruling',
            'attacks and carrying while entangled are blocked by this restricted host']}
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2, default=sorted) + '\n')
    print('Audited grapple demonstration saved; no statistical conclusion is implied.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
