"""Save a replayable, audited Fast Strikes example while Victor is pinned."""

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
from experimental.entangled_attack_audit import audit_entangled_attacks
from experimental.entangled_attack_duel import EntangledAttackDuel, EntangledAttackPolicy
from scripts.crossbones_grapple_demo import EXTRA as PRIOR_SOURCES
from scripts.crossbones_ram_demo import EVIDENCE, VICTOR
from scripts.current_study_dev import ROOT, source_commit

SEED = 7
EXTRA = tuple(sorted(set(PRIOR_SOURCES + ('ENTANGLED_ATTACK_EXPERIMENT.md',
    'experimental/entangled_attack_duel.py', 'experimental/entangled_attack_audit.py',
    'scripts/entangled_attack_demo.py'))))


def sources(policies):
    result = _source_manifest(policies, None)
    result.update({name: sha256((ROOT / name).read_bytes()).hexdigest() for name in EXTRA})
    return result


def run(output):
    path = Path(output)
    if path.resolve().is_relative_to((ROOT / 'results').resolve()):
        raise ValueError('Experimental results must not enter certified results inventory')
    require_new_output(path)
    subset = build_crossbones_grapple_subset(json.loads(EVIDENCE.read_text(encoding='utf-8')),
                                                accept_incomplete=True)
    sheet = load_sheet(VICTOR)
    profiles = (subset.profile, compile_duel(sheet))
    policies = (EntangledAttackPolicy('crossbones', prefer_grapple=True, prefer_stopping=True,
                                      use_ram=False, attack_when_grabbing=True),
                EntangledAttackPolicy('victor', weapon='hammer', offhand='blade', prefer_fast=True,
                                      shield_react=True, use_ram=False, escape_reaction=False,
                                      attack_when_grabbed=True))
    weapons = (subset.ranged_weapon, 'generic')
    declared = (profiles[0].name,)
    before = sources(policies)
    commit = source_commit(before)
    duel = EntangledAttackDuel(profiles, policies, seed=SEED, initial_prone=(False, False),
        initial_distance=1, max_rounds=4, audit=True, action_registry=DEFAULT_ACTIONS,
        ranged_weapons=weapons, stop_on_attacker=profiles[1].name, declared_armed_lethal=declared,
        escape_trigger_mode='attack', inside_attack_trouble=True)
    result = duel.run()
    issues = audit_entangled_attacks(result, profiles, inside_attack_trouble=True,
        declared_armed_lethal=declared, escape_trigger_mode='attack', ranged_weapons=weapons,
        initial_prone=(False, False), initial_distance=1, expected_seed=SEED, max_rounds=4,
        ruleset=duel.table_ruleset, self_damage_mode='stop_before_heal_reject_lethal',
        stop_on_attacker=profiles[1].name)
    if issues:
        raise RuntimeError(f'Entangled attack audit failed: {issues}')
    markers = [e for e in result.log if e.get('type') == 'entangled_attack_check' and e.get('pinned')]
    if ([e['mode'] for e in markers] != ['hammer_fast', 'blade_fast']
            or any(e['added_troubles'] != 2 for e in markers)):
        raise RuntimeError('Selected seed must exercise both pinned Fast limbs')
    require_unchanged_sources(before, sources(policies))
    if source_commit(before) != commit:
        raise RuntimeError('Example source commit changed')
    payload = {'schema': 'blacklight-experimental-entangled-attack-demo-v1',
        'source_commit': commit, 'source_sha256': before, 'seed': SEED,
        'crossbones_subset': asdict(subset), 'victor_sheet': sheet_record(sheet),
        'profiles': [asdict(p) for p in profiles], 'policies': [asdict(p) for p in policies],
        'policy_types': [f'{type(p).__module__}.{type(p).__qualname__}' for p in policies],
        'ranged_weapons': weapons, 'declared_armed_lethal': declared, 'escape_trigger_mode': 'attack',
        'inside_attack_trouble': True, 'initial_distance': 1, 'initial_prone': [False, False],
        'max_rounds': 4, 'ruleset': duel.table_ruleset,
        'self_damage_mode': 'stop_before_heal_reject_lethal', 'stop_on_attacker': profiles[1].name,
        'result': asdict(result), 'audit_issues': issues,
        'limitations': ['single selected example, not an efficacy study', 'incomplete official profile',
            'inside-attack trouble and trigger identity are hypotheses, not table rulings',
            'self-hit, third parties, carrying, knockback and counterattacks while held are not modeled']}
    write_new_text(path, json.dumps(payload, ensure_ascii=False, indent=2, default=sorted) + '\n')
    print('Audited entangled attack demonstration saved; no statistical conclusion is implied.')


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)


if __name__ == '__main__':
    main()
