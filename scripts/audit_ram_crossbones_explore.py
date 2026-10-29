"""Independently check exploratory record accounting and frozen source identity."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from math import isfinite, sqrt
from pathlib import Path
import re
import subprocess

from scripts.verify_sources import ROOT, snapshot_source_hash


SCENARIOS = ('stationary', 'kite')
STRATEGIES = ('hammer', 'fast_hammer', 'fast_blade')
STATUSES = ('victory', 'defeat', 'draw', 'inconclusive', 'unresolved_death_threshold')
HEX = re.compile(r'[0-9a-f]{64}')
REQUIRED_SOURCES = {
    'RAM_CROSSBONES_EXPLORATION_SPEC.md', 'scripts/ram_crossbones_explore.py',
    'scripts/audit_ram_crossbones_explore.py', 'scripts/replay_ram_crossbones_explore.py',
    'character_evidence/crossbones_core_p155.json',
    'characters/victor_halle/rank3_2026-10-27_split_fast.json',
    'experimental/crossbones_subset.py', 'experimental/stopping_ram_duel.py',
    'experimental/stopping_duel.py', 'experimental/stopping_audit.py',
    'experimental/parry_duel.py', 'experimental/parry_audit.py',
    'experimental/point_blank_parry.py', 'experimental/reaction_pools.py',
    'experimental/smg_duel.py', 'experimental/smg_audit.py',
    'experimental/ranged_powers_duel.py', 'experimental/ranged_powers_audit.py',
    'experimental/slow_motion_duel.py', 'experimental/slow_motion_dodge.py',
    'experimental/double_tap_duel.py', 'experimental/double_tap_audit.py',
    'experimental/nonlethal_ram_duel.py', 'experimental/nonlethal_ram_audit.py',
    'experimental/ram_incapacity_duel.py', 'experimental/ram_stop_audit.py',
    'experimental/incapacity_endturn_audit.py', 'experimental/ram_prone_duel.py',
    'experimental/ram_prone_audit.py', 'experimental/ram_opportunity_duel.py',
    'experimental/ram_opportunity_audit.py', 'experimental/ram_trigger.py',
    'experimental/ram_transaction.py', 'experimental/ram_record.py',
    'experimental/ram_record_audit.py', 'experimental/ram_impact.py',
    'experimental/ram_rolled.py', 'experimental/prone.py', 'experimental/prone_duel.py',
    'experimental/prone_duel_audit.py', 'blacklight/engine.py', 'blacklight/dice.py',
    'blacklight/pool_damage.py', 'blacklight/audit.py', 'blacklight/profile_audit.py',
    'blacklight/result_audit.py', 'blacklight/turn_audit.py', 'blacklight/spatial_audit.py',
    'blacklight/split_audit.py', 'combatants/sheets.py', 'combatants/duel_adapter.py',
    'combatants/split_fast.py', 'combatants/modular_duel.py', 'combatants/actions.py',
}


def expected_policies(scenario, strategy, use_ram):
    common = {'open_stance': False, 'heal_missing': None, 'heal_spend': 15, 'prefer_fast': False,
              'weapon': 'bare', 'offhand': None, 'kite': False, 'riposte': True,
              'move_after_attack': False, 'knockback_stance': True, 'edge_mode': 'hit',
              'always_wait': False, 'dodge_below_health': None, 'treat_bleeding': False,
              'shield_react': False, 'shield_standard': False, 'shield_end_turn': False,
              'effect_limb': 0, 'stand_when_prone': True, 'use_ram': False,
              'prefer_double_tap': True, 'dodge_agility_attacks': True, 'prefer_parry': True,
              'prefer_fast_hands': True, 'prefer_stopping': False, 'use_stopping_followup': True}
    foe = dict(common, name=('crossbones_parcial_estacionario' if scenario == 'stationary'
                             else 'crossbones_parcial_recuo'), prefer_stopping=True,
               treat_bleeding=True, kite=scenario == 'kite', move_after_attack=scenario == 'kite')
    hero = dict(common, name='victor_' + strategy, weapon='hammer',
                offhand=None if strategy == 'hammer' else 'blade', prefer_fast=strategy != 'hammer',
                effect_limb=int(strategy == 'fast_blade'), use_ram=use_ram,
                shield_react=True, knockback_stance=False)
    return [foe, hero]


def exact_mapping(actual, expected):
    return (isinstance(actual, dict) and set(actual) == set(expected)
            and all(type(actual[key]) is type(value) and actual[key] == value
                    for key, value in expected.items()))


def independent_wilson(k, n):
    z = 1.959963984540054
    p = k / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return max(0.0, center - half), min(1.0, center + half)


def audit(data, *, verify_snapshots=True):
    if type(verify_snapshots) is not bool:
        raise ValueError('Snapshot verification choice must be boolean')
    if not isinstance(data, dict) or data.get('schema') != 'blacklight-experimental-ram-crossbones-explore-v1':
        return ['Invalid exploration schema']
    n = data.get('n_per_cell')
    if (type(n) is not int or not 1 <= n <= 1000 or type(data.get('matches_preregistration')) is not bool
            or data['matches_preregistration'] is not (n == 1000)
            or data.get('initial_distance') != 10 or data.get('max_rounds') != 30
            or data.get('self_damage_mode') != 'stop_before_heal_reject_lethal'):
        return ['Invalid preregistered configuration']
    cells = data.get('cells')
    if not isinstance(cells, list) or len(cells) != 12:
        return ['The exploration must contain twelve cells']
    source = data.get('source_sha256')
    commit = data.get('source_commit')
    if not isinstance(source, dict) or not source or not isinstance(commit, str):
        return ['Missing source manifest']
    issues = []
    if not REQUIRED_SOURCES.issubset(source):
        issues.append('Source manifest omits required mechanics or audit files')
    if data.get('spec') != 'RAM_CROSSBONES_EXPLORATION_SPEC.md':
        issues.append('Unexpected preregistration path')
    subset = data.get('crossbones_subset')
    profile = subset.get('profile') if isinstance(subset, dict) else None
    powers = profile.get('powers') if isinstance(profile, dict) else None
    minimum_profile = {'name': 'Crossbones (recorte experimental)', 'rank': 3, 'max_health': 90,
                       'max_focus': 90, 'melee': 4, 'agility': 5, 'resilience': 3, 'vigilance': 2,
                       'melee_defense': 14, 'agility_defense': 15, 'run_speed': 6,
                       'health_dr': 0, 'melee_bonus': 0, 'logic': 1, 'run_speed_exception': False,
                       'shield_active': False,
                       'ranged_bonus': 2, 'ranged_range': 10, 'ranged_is_ammunition': True,
                       'initiative_modifier': 2, 'heroic': False}
    if (not isinstance(profile, dict) or any(type(profile.get(key)) is not type(value)
            or profile.get(key) != value for key, value in minimum_profile.items())
            or not isinstance(powers, list) or any(not isinstance(power, str) for power in powers)
            or set(powers) != {'accuracy', 'slow_motion_dodge', 'double_tap',
                               'fast_hands', 'point_blank_parry', 'stopping_power'}
            or profile.get('traits') != ['battle_ready', 'situational_awareness']
            or profile.get('weapons') != []
            or subset.get('included_powers') != ['Accuracy 2', 'Double Tap', 'Fast Hands',
                    'Point-Blank Parry', 'Slow-Motion Dodge', 'Stopping Power']
            or subset.get('omitted_powers') != ['Banging Heads', 'Grappling Technique', 'Dance of Death',
                    'Slow-Motion Shoot-Dodge', 'Snap Shooting', 'Weapons Blazing']
            or subset.get('omitted_traits') != ['Bloodthirsty', 'Combat Expert',
                    'Connections: Military (Hydra)', 'Determination', 'Piloting']
            or subset.get('omitted_tags') != ['Backup', 'Public Identity', 'Villainous',
                                               'Signature Weapon: Submachine Gun']
            or subset.get('ranged_weapon') != 'submachine_gun'):
        issues.append('Unexpected Crossbones subset')
    if verify_snapshots:
        try:
            for name, expected in source.items():
                if not isinstance(expected, str) or HEX.fullmatch(expected) is None:
                    issues.append(f'Invalid source digest: {name}')
                elif snapshot_source_hash(ROOT, commit, name) != expected:
                    issues.append(f'Source mismatch: {name}')
        except (TypeError, ValueError, OSError) as error:
            issues.append(f'Invalid source snapshot: {error}')
        try:
            raw = subprocess.run(['git', '--no-replace-objects', 'show',
                f'{commit}:characters/victor_halle/rank3_2026-10-27_split_fast.json'], cwd=ROOT,
                capture_output=True, text=True, encoding='utf-8', check=True).stdout
            if data.get('victor_sheet') != json.loads(raw):
                issues.append('Victor sheet differs from the frozen source')
        except (OSError, subprocess.SubprocessError, ValueError, TypeError) as error:
            issues.append(f'Unable to check frozen Victor sheet: {error}')
    expected_cells = {(s, p, r) for s in SCENARIOS for p in STRATEGIES for r in (False, True)}
    found = set()
    for cell in cells:
        if not isinstance(cell, dict):
            issues.append('Invalid cell')
            continue
        scenario, strategy, use_ram = cell.get('scenario'), cell.get('strategy'), cell.get('use_ram')
        if scenario not in SCENARIOS or strategy not in STRATEGIES or type(use_ram) is not bool:
            issues.append('Unknown cell identity')
            continue
        identity = (scenario, strategy, use_ram)
        if identity in found:
            issues.append(f'Duplicate cell: {identity}')
        found.add(identity)
        actual_policies = cell.get('policies')
        expected = expected_policies(scenario, strategy, use_ram)
        expected_types = [{'module': ('scripts.ram_crossbones_explore' if scenario == 'stationary'
                                      else 'experimental.stopping_duel'),
                           'class': 'StationaryPolicy' if scenario == 'stationary' else 'StoppingPolicy'},
                          {'module': 'experimental.stopping_duel', 'class': 'StoppingPolicy'}]
        if (not isinstance(actual_policies, list) or len(actual_policies) != 2
                or not all(exact_mapping(a, b) for a, b in zip(actual_policies, expected))
                or cell.get('policy_types') != expected_types):
            issues.append(f'Policy mismatch: {identity}')
        rows, summary = cell.get('records'), cell.get('summary')
        if not isinstance(rows, list) or len(rows) != n or not isinstance(summary, dict):
            issues.append(f'Invalid records: {identity}')
            continue
        counts = dict.fromkeys(STATUSES, 0)
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                issues.append(f'Invalid record at {identity}/{index}')
                continue
            status = row.get('status')
            expected_seed = int.from_bytes(sha256(
                f'blacklight-ram-crossbones-explore-v1:{scenario}:{index}'.encode('utf-8')).digest()[:8], 'big')
            if (type(row.get('index')) is not int or row['index'] != index
                    or type(row.get('seed')) is not int or row['seed'] != expected_seed
                    or status not in counts):
                issues.append(f'Invalid seed or status at {identity}/{index}')
                continue
            counts[status] += 1
            if status == 'unresolved_death_threshold':
                if (row.get('audit') != 'incomplete_prefix_replay_required'
                        or row.get('unresolved_replayed') is not True
                        or type(row.get('raw_health_after')) is not int
                        or type(row.get('death_threshold')) is not int
                        or row['death_threshold'] != -150 or row['raw_health_after'] > row['death_threshold']
                        or not isinstance(row.get('prefix_sha256'), str)
                        or HEX.fullmatch(row['prefix_sha256']) is None):
                    issues.append(f'Invalid unresolved record at {identity}/{index}')
            else:
                hp = row.get('final_health')
                rounds = row.get('rounds')
                if (row.get('audit') != 'complete_duel_passed' or not isinstance(hp, list) or len(hp) != 2
                        or any(type(value) is not int for value in hp) or type(rounds) is not int
                        or not 0 <= rounds <= 30 or not isinstance(row.get('result_sha256'), str)
                        or HEX.fullmatch(row['result_sha256']) is None):
                    issues.append(f'Invalid completed record at {identity}/{index}')
                    continue
                expected_status = ('victory' if hp[1] > 0 and hp[0] <= 0 else
                                   'defeat' if hp[0] > 0 and hp[1] <= 0 else
                                   'draw' if hp[0] <= 0 and hp[1] <= 0 else 'inconclusive')
                if status != expected_status or status == 'inconclusive' and rounds != 30:
                    issues.append(f'Outcome inconsistent with Health at {identity}/{index}')
                foe, hero, remaining_focus = (row.get('opponent_metrics'), row.get('victor_metrics'),
                                              row.get('final_focus'))
                if (not isinstance(foe, dict) or not isinstance(hero, dict)
                        or not isinstance(remaining_focus, list) or len(remaining_focus) != 2
                        or any(type(value) is not int for value in remaining_focus)
                        or any(type(stats.get(key)) is not int or stats[key] < 0
                               for stats in (foe, hero) for key in ('damage_taken', 'healing_effective',
                                                                   'focus_spent', 'attacks', 'hits', 'fantastic_hits'))
                        or any(type(row.get(key)) is not int or row[key] < 0
                               for key in ('ram_attacks', 'stopping_uses', 'parries'))):
                    issues.append(f'Invalid metrics at {identity}/{index}')
                    continue
                if (any(stats['fantastic_hits'] > stats['hits'] or stats['hits'] > stats['attacks']
                        for stats in (foe, hero)) or 90 - foe['damage_taken'] + foe['healing_effective'] != hp[0]
                        or 150 - hero['damage_taken'] + hero['healing_effective'] != hp[1]
                        or 90 - foe['focus_spent'] != remaining_focus[0]
                        or 90 - hero['focus_spent'] != remaining_focus[1]
                        or not use_ram and row['ram_attacks'] != 0):
                    issues.append(f'Metrics inconsistent with state at {identity}/{index}')
        if summary.get('n') != n or summary.get('counts') != counts:
            issues.append(f'Summary count mismatch: {identity}')
        k, unresolved = counts['victory'], counts['unresolved_death_threshold']
        wanted = (k / n, (k + unresolved) / n)
        interval = independent_wilson(k, n)
        fields = ((summary.get('recorded_victory_fraction'), wanted[0]),)
        bounds, wilson = summary.get('victory_identification_bounds'), summary.get('recorded_victory_wilson_95')
        if not isinstance(bounds, list) or len(bounds) != 2 or not isinstance(wilson, list) or len(wilson) != 2:
            issues.append(f'Missing uncertainty fields: {identity}')
        else:
            fields += tuple(zip(bounds, wanted)) + tuple(zip(wilson, interval))
            if any(type(actual) not in (int, float) or not isfinite(actual)
                   or abs(actual - expected) > 1e-12
                   for actual, expected in fields):
                issues.append(f'Uncertainty field mismatch: {identity}')
    if found != expected_cells:
        issues.append('Exploration cell grid is incomplete')
    return issues


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    data = json.loads(args.path.read_text(encoding='utf-8'))
    issues = audit(data)
    if issues:
        raise SystemExit('\n'.join(issues))
    print('Exploration accounting and frozen sources passed; individual duel traces require replay.')


if __name__ == '__main__':
    main()
