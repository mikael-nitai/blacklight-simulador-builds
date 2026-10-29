"""Independent accounting and source checks for the grapple exploration."""

from argparse import ArgumentParser
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
import subprocess

from scripts.audit_ram_crossbones_explore import exact_mapping, expected_policies, independent_wilson
from scripts.verify_sources import ROOT, snapshot_source_hash

HEX = re.compile(r'[0-9a-f]{64}')
STATUSES = ('victory', 'defeat', 'draw', 'inconclusive')
REQUIRED = {'GRAPPLE_STRATEGY_EXPLORATION_SPEC.md', 'scripts/grapple_strategy_explore.py',
    'scripts/audit_grapple_strategy_explore.py', 'scripts/replay_grapple_strategy_explore.py',
    'scripts/audit_ram_crossbones_explore.py', 'scripts/verify_sources.py', 'scripts/current_study_dev.py',
    'characters/victor_halle/rank3_2026-10-27_split_fast.json', 'character_evidence/crossbones_core_p155.json',
    'experimental/crossbones_grapple_subset.py', 'experimental/crossbones_reactive_grapple_subset.py',
    'experimental/grappling.py',
    'experimental/grappling_audit.py', 'experimental/grappling_duel.py',
    'experimental/grappling_duel_audit.py', 'experimental/entangled_attack_duel.py',
    'experimental/entangled_attack_audit.py', 'experimental/entangled_reaction_duel.py',
    'experimental/entangled_reaction_audit.py', 'experimental/stopping_duel.py',
    'experimental/stopping_audit.py', 'experimental/parry_duel.py', 'experimental/parry_audit.py',
    'experimental/smg_duel.py', 'experimental/smg_audit.py', 'experimental/ranged_powers_duel.py',
    'experimental/ranged_powers_audit.py', 'experimental/nonlethal_ram_duel.py',
    'experimental/nonlethal_ram_audit.py', 'experimental/ram_prone_duel.py',
    'experimental/ram_prone_audit.py', 'blacklight/engine.py', 'blacklight/dice.py',
    'blacklight/dice_audit.py', 'blacklight/audit.py', 'blacklight/profile_audit.py',
    'blacklight/result_audit.py', 'blacklight/pool_damage.py', 'combatants/split_fast.py',
    'combatants/actions.py', 'combatants/sheets.py', 'combatants/duel_adapter.py'}


def expected_for(strategy):
    foe, hero = expected_policies('stationary', 'fast_hammer', False)
    foe['name'] = 'crossbones_grapple'
    hero['name'] = 'victor_' + strategy
    added = {'prefer_grapple': False, 'escape_reaction': True, 'release_hold': False,
             'attack_when_grabbed': False, 'attack_when_grabbing': False, 'use_entangled_reactions': True}
    foe.update(added, prefer_grapple=True, attack_when_grabbing=True)
    hero.update(added, escape_reaction=strategy == 'escape', attack_when_grabbed=strategy == 'attack')
    return foe, hero


def audit(data, *, verify_snapshots=True):
    if type(verify_snapshots) is not bool:
        raise ValueError('Snapshot verification must be boolean')
    if not isinstance(data, dict) or data.get('schema') != 'blacklight-experimental-grapple-strategy-explore-v1':
        return ['Invalid study schema']
    n = data.get('n_per_cell')
    if (type(n) is not int or not 1 <= n <= 1000 or type(data.get('matches_preregistration')) is not bool
            or data['matches_preregistration'] is not (n == 1000) or data.get('initial_distance') != 1
            or data.get('max_rounds') != 30 or data.get('spec') != 'GRAPPLE_STRATEGY_EXPLORATION_SPEC.md'):
        return ['Invalid preregistered configuration']
    cells, sources, commit = data.get('cells'), data.get('source_sha256'), data.get('source_commit')
    if (not isinstance(cells, list) or len(cells) != 8 or not isinstance(sources, dict)
            or not REQUIRED.issubset(sources) or not isinstance(commit, str)):
        return ['Missing cells or source manifest']
    issues = []
    runtime = data.get('runtime')
    if (not isinstance(runtime, dict) or set(runtime) != {'python_version', 'python_implementation'}
            or not isinstance(runtime.get('python_version'), str)
            or re.fullmatch(r'\d+\.\d+\.\d+', runtime['python_version']) is None
            or not isinstance(runtime.get('python_implementation'), str)
            or not runtime['python_implementation']):
        issues.append('Missing runtime identity')
    subset = data.get('crossbones_subset')
    profile = subset.get('profile') if isinstance(subset, dict) else None
    powers = profile.get('powers') if isinstance(profile, dict) else None
    included = subset.get('included_powers') if isinstance(subset, dict) else None
    omitted = subset.get('omitted_powers') if isinstance(subset, dict) else None
    scalar_profile = {'name': 'Crossbones (recorte experimental)', 'rank': 3, 'max_health': 90,
        'max_focus': 90, 'melee': 4, 'agility': 5, 'resilience': 3, 'vigilance': 2,
        'melee_defense': 14, 'agility_defense': 15, 'run_speed': 6, 'health_dr': 0,
        'melee_bonus': 0, 'ranged_bonus': 2, 'ranged_range': 10, 'ranged_is_ammunition': True,
        'logic': 1, 'initiative_modifier': 2, 'run_speed_exception': False,
        'shield_active': False, 'heroic': False}
    if (not isinstance(profile, dict) or profile.get('name') != 'Crossbones (recorte experimental)'
            or any(type(profile.get(k)) is not type(v) or profile.get(k) != v for k, v in scalar_profile.items())
            or not isinstance(powers, list) or any(not isinstance(x, str) for x in powers)
            or set(powers) != {'accuracy', 'slow_motion_dodge', 'double_tap',
                 'fast_hands', 'point_blank_parry', 'stopping_power', 'grappling_technique'}
            or profile.get('traits') != ['battle_ready', 'situational_awareness'] or profile.get('weapons') != []
            or subset.get('ranged_weapon') != 'submachine_gun'
            or included != ['Accuracy 2', 'Double Tap', 'Fast Hands', 'Grappling Technique',
                            'Point-Blank Parry', 'Slow-Motion Dodge', 'Stopping Power']
            or omitted != ['Banging Heads', 'Dance of Death', 'Slow-Motion Shoot-Dodge',
                           'Snap Shooting', 'Weapons Blazing']
            or subset.get('included_traits') != ['Battle Ready', 'Situational Awareness']
            or subset.get('omitted_traits') != ['Bloodthirsty', 'Combat Expert',
                'Connections: Military (Hydra)', 'Determination', 'Piloting']
            or subset.get('omitted_tags') != ['Backup', 'Public Identity', 'Villainous',
                                               'Signature Weapon: Submachine Gun']
            or not isinstance(subset.get('assumptions'), list)
            or 'The grapple host restricts actors in a hold to escape, release or wait.' in subset['assumptions']
            or 'Close attacks and miss reactions between the two held actors are modeled.' not in subset['assumptions']):
        issues.append('Unexpected partial Crossbones profile')
    if verify_snapshots:
        try:
            for name, value in sources.items():
                if (not isinstance(value, str) or HEX.fullmatch(value) is None
                        or snapshot_source_hash(ROOT, commit, name) != value):
                    issues.append(f'Source mismatch: {name}')
            raw = subprocess.run(['git', '--no-replace-objects', 'show',
                f'{commit}:characters/victor_halle/rank3_2026-10-27_split_fast.json'], cwd=ROOT,
                capture_output=True, text=True, encoding='utf-8', check=True).stdout
            if data.get('victor_sheet') != json.loads(raw):
                issues.append('Victor sheet differs from frozen source')
        except (TypeError, ValueError, OSError, subprocess.SubprocessError) as error:
            issues.append(f'Invalid source snapshot: {error}')
    expected_cells = {(strategy, trouble, mode) for strategy in ('escape', 'attack')
                      for trouble in (False, True) for mode in ('attack', 'condition')}
    found = set()
    for cell in cells:
        if not isinstance(cell, dict):
            issues.append('Invalid cell')
            continue
        strategy, trouble, mode = cell.get('strategy'), cell.get('inside_attack_trouble'), cell.get('trigger_mode')
        if strategy not in ('escape', 'attack') or type(trouble) is not bool or mode not in ('attack', 'condition'):
            issues.append('Invalid cell identity')
            continue
        identity = (strategy, trouble, mode)
        if identity in found:
            issues.append(f'Duplicate cell {identity}')
        found.add(identity)
        policies = cell.get('policies')
        if (not isinstance(policies, list) or len(policies) != 2
                or not all(exact_mapping(actual, expected) for actual, expected in zip(policies, expected_for(strategy)))
                or cell.get('policy_types') != ['experimental.entangled_reaction_duel.EntangledReactionPolicy'] * 2):
            issues.append(f'Policy mismatch {identity}')
        rows, summary = cell.get('records'), cell.get('summary')
        if not isinstance(rows, list) or len(rows) != n or not isinstance(summary, dict):
            issues.append(f'Invalid records {identity}')
            continue
        counts = dict.fromkeys(STATUSES, 0)
        totals = dict.fromkeys(('grapple_hits', 'reaction_escapes', 'standard_escapes', 'held_attacks'), 0)
        health_total, focus_total, ever_grabbed = 0, 0, 0
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                issues.append(f'Invalid record {identity}/{index}')
                continue
            seed = int.from_bytes(sha256(f'blacklight-grapple-explore-v1:{index}'.encode()).digest()[:8], 'big')
            keys = ('grapple_attempts', 'grapple_hits', 'grapple_fantastic', 'reaction_escapes',
                    'standard_escapes', 'held_attacks')
            hp, fp, rounds, status = row.get('final_health'), row.get('final_focus'), row.get('rounds'), row.get('status')
            if (type(row.get('index')) is not int or row['index'] != index or type(row.get('seed')) is not int
                    or row['seed'] != seed or status not in counts or row.get('audit') != 'complete_duel_passed'
                    or not isinstance(row.get('result_sha256'), str) or HEX.fullmatch(row['result_sha256']) is None
                    or any(type(row.get(k)) is not int or row[k] < 0 for k in keys)
                    or not isinstance(hp, list) or len(hp) != 2 or any(type(x) is not int for x in hp)
                    or not isinstance(fp, list) or len(fp) != 2 or any(type(x) is not int for x in fp)
                    or type(rounds) is not int or not 0 <= rounds <= 30):
                issues.append(f'Invalid record facts {identity}/{index}')
                continue
            expected = ('victory' if hp[1] > 0 and hp[0] <= 0 else
                        'defeat' if hp[0] > 0 and hp[1] <= 0 else
                        'draw' if hp[0] <= 0 and hp[1] <= 0 else 'inconclusive')
            if (expected != status or status == 'inconclusive' and rounds != 30
                    or row['grapple_fantastic'] > row['grapple_hits']
                    or row['grapple_hits'] > row['grapple_attempts']
                    or row['reaction_escapes'] > row['grapple_hits']
                    or strategy == 'attack' and (row['reaction_escapes'] or row['standard_escapes'])
                    or not 0 <= fp[0] <= 90 or not 0 <= fp[1] <= 90):
                issues.append(f'Inconsistent outcome or metrics {identity}/{index}')
            counts[status] += 1
            health_total += hp[1]
            focus_total += fp[1]
            ever_grabbed += int(row['grapple_hits'] > 0)
            for key in totals:
                totals[key] += row[key]
        expected_summary = {'n': n, 'counts': counts, 'ever_grabbed': ever_grabbed, **totals}
        for key, value in expected_summary.items():
            if type(summary.get(key)) is not type(value) or summary[key] != value:
                issues.append(f'Summary mismatch {identity}/{key}')
        numerical = [(summary.get('victory_fraction'), counts['victory'] / n),
                     (summary.get('mean_victor_final_health'), health_total / n),
                     (summary.get('mean_victor_final_focus'), focus_total / n)]
        interval = summary.get('victory_wilson_95')
        if not isinstance(interval, list) or len(interval) != 2:
            issues.append(f'Missing Wilson interval {identity}')
        else:
            numerical += list(zip(interval, independent_wilson(counts['victory'], n)))
        if any(type(actual) not in (int, float) or not isfinite(actual) or abs(actual - expected) > 1e-12
               for actual, expected in numerical):
            issues.append(f'Summary uncertainty or mean mismatch {identity}')
    if found != expected_cells:
        issues.append('Missing cells')
    return issues


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    issues = audit(json.loads(args.path.read_text(encoding='utf-8')))
    if issues:
        raise SystemExit('\n'.join(issues))
    print('Independent accounting and frozen sources passed; sample replay is a separate check.')


if __name__ == '__main__':
    main()
