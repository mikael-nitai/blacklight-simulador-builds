"""Preserve one audited example of a shield-aware partial official opponent."""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path

from blacklight.results_io import require_new_output, require_unchanged_sources, write_new_text
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.sheets import load_sheet, sheet_record
from experimental.adaptive_armed_melee import DeclaredArmedMeleeDuel, ShieldAwarePolicy
from experimental.adaptive_armed_melee_audit import audit_declared_armed_melee
from experimental.crossbones_subset import build_crossbones_stopping_subset
from experimental.stopping_duel import StoppingPolicy
from scripts.crossbones_ram_demo import EVIDENCE, EXTRA as RAM_SOURCES, VICTOR
from scripts.current_study_dev import ROOT, source_commit
from combatants.runner import _source_manifest

SEED = 3
EXTRA = tuple(sorted(set(RAM_SOURCES + ('ADAPTIVE_ARMED_MELEE_EXPERIMENT.md',
    'experimental/adaptive_armed_melee.py', 'experimental/adaptive_armed_melee_audit.py',
    'scripts/adaptive_armed_melee_demo.py'))))


def sources(policies):
    result = _source_manifest(policies, None)
    result.update({name: sha256((ROOT / name).read_bytes()).hexdigest() for name in EXTRA})
    return result


def run(output):
    path = Path(output)
    if path.resolve().is_relative_to((ROOT / 'results').resolve()):
        raise ValueError('Experimental results must not enter the certified results inventory')
    require_new_output(path)
    subset = build_crossbones_stopping_subset(json.loads(EVIDENCE.read_text(encoding='utf-8')),
                                                accept_incomplete=True)
    sheet = load_sheet(VICTOR)
    profiles = (subset.profile, compile_duel(sheet))
    policies = (ShieldAwarePolicy('crossbones', prefer_stopping=True, use_ram=False,
                                  treat_bleeding=True, kite=True, move_after_attack=True),
                StoppingPolicy('victor', weapon='hammer', shield_react=True, use_ram=False))
    weapons = (subset.ranged_weapon, 'generic')
    declared = (profiles[0].name,)
    before = sources(policies)
    commit = source_commit(before)
    duel = DeclaredArmedMeleeDuel(profiles, policies, seed=SEED, initial_prone=(False, False),
        initial_distance=10, max_rounds=10, audit=True, action_registry=DEFAULT_ACTIONS,
        ranged_weapons=weapons, stop_on_attacker=profiles[1].name, declared_armed_lethal=declared)
    result = duel.run()
    issues = audit_declared_armed_melee(result, profiles, declared_armed_lethal=declared,
        ranged_weapons=weapons, initial_prone=(False, False), initial_distance=10,
        expected_seed=SEED, max_rounds=10, ruleset=duel.table_ruleset,
        self_damage_mode='stop_before_heal_reject_lethal', stop_on_attacker=profiles[1].name)
    if issues:
        raise RuntimeError(f'Declared melee audit failed: {issues}')
    if (not any(e.get('type') == 'attack' and e.get('mode') == 'ranged' and e.get('actor') == declared[0]
                for e in result.log)
            or not any(e.get('type') == 'attack' and e.get('declared_lethality') == 'lethal'
                       and e.get('actor') == declared[0] for e in result.log)):
        raise RuntimeError('The selected example must exercise both ranged and declared melee')
    require_unchanged_sources(before, sources(policies))
    if source_commit(before) != commit:
        raise RuntimeError('Example source commit changed')
    payload = {'schema': 'blacklight-experimental-adaptive-armed-melee-demo-v1',
        'source_commit': commit, 'source_sha256': before, 'seed': SEED,
        'crossbones_subset': asdict(subset), 'victor_sheet': sheet_record(sheet),
        'profiles': [asdict(p) for p in profiles], 'policies': [asdict(p) for p in policies],
        'policy_types': [f'{type(p).__module__}.{type(p).__qualname__}' for p in policies],
        'ranged_weapons': weapons, 'declared_armed_lethal': declared,
        'initial_distance': 10, 'initial_prone': [False, False], 'max_rounds': 10,
        'ruleset': duel.table_ruleset, 'self_damage_mode': 'stop_before_heal_reject_lethal',
        'stop_on_attacker': profiles[1].name, 'result': asdict(result), 'audit_issues': issues,
        'limitations': ['single selected example; no strategy or statistical conclusion',
                        'incomplete Crossbones; omitted features listed in the subset',
                        'declared lethal is a scenario choice, not a ruling on armed bare attack defaults']}
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2, default=sorted) + '\n')
    print('Audited adaptive armed-melee demonstration saved; no statistical conclusion is implied.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
