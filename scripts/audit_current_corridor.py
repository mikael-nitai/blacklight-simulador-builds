"""Independent, read-only gates for the current Fast Strikes corridor adapter.

Run: python -B -m scripts.audit_current_corridor

Only this script is retained. The CLI smoke uses a temporary directory that is
removed before the audit returns; no combat results are written to the repo.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory, gettempdir

from blacklight.audit import audit_log
from blacklight.engine import Duel, Move, blacklight_profile
from blacklight.experiment import ROOT, scenarios
from blacklight.policies import ATTACK, HAMMER, KITER, SHIELD_BLADE_HAMMER_REACTIVE
from combatants.battlefields import CorridorMap
from combatants.runner import run_batch, run_duel
from combatants.sheets import load_sheet
from combatants.split_fast import SplitFastDuel, SplitFastPolicy
from combatants.terrain_policies import WallAwarePolicy
from experimental.corridor import CorridorDuel, CorridorGeometry, SplitFastCorridorDuel
from experimental.corridor_audit import audit_corridor
from .audit_manifest import audit_source_manifest, require_audit_sources_unchanged


BASELINE_COMMIT = 'a6cfd28'


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def gunner():
    return next(item.opponent for item in scenarios() if item.id == 'gunner_kiter')


def check_audits(duel, result, initial_positions: tuple[int, int], length: int) -> None:
    profiles = tuple(f.profile for f in duel.fighters)
    issues = audit_log(result.log,
                       {p.name: p.max_health for p in profiles},
                       {p.name: p.max_focus for p in profiles})
    issues += audit_corridor(result.log, tuple(p.name for p in profiles),
                             initial_positions=initial_positions, length=length,
                             final_positions=tuple(duel.positions),
                             wall_reached=duel.wall_reached,
                             contact_occurred=duel.contact_occurred)
    require(not issues, f'auditors_rejected_trace:{issues[:4]}')
    require(0 <= duel.positions[0] < duel.positions[1] <= length,
            'final_position_out_of_bounds')
    require(duel.distance == duel.positions[1] - duel.positions[0],
            'final_distance_position_mismatch')


def equivalent_contact() -> dict:
    mro = SplitFastCorridorDuel.__mro__
    require(CorridorGeometry in mro and SplitFastDuel in mro and Duel in mro,
            'missing_mro_component')
    require(mro.index(CorridorGeometry) < mro.index(SplitFastDuel) < mro.index(Duel),
            'noncooperative_mro_order')
    hero = blacklight_profile()
    foe = replace(hero, name='Contact Target')
    policies = (
        SplitFastPolicy('blade_hammer', weapon='blade', offhand='hammer',
                        prefer_fast=True, effect_limb=1),
        SplitFastPolicy('shield_hammer', weapon='hammer', prefer_fast=True,
                        shield_react=True, effect_limb=0),
    )
    fast_uses = 0
    for seed in range(50):
        common = {'seed': seed, 'max_rounds': 3, 'audit': True}
        open_duel = SplitFastDuel((hero, foe), policies, initial_distance=1, **common)
        mapped_duel = SplitFastCorridorDuel(
            (hero, foe), policies, length=12, initial_positions=(0, 1), **common)
        open_result = asdict(open_duel.run())
        mapped_actual = mapped_duel.run()
        mapped_result = asdict(mapped_actual)
        fast_uses += sum(row['type'] == 'fast_use_start' for row in mapped_result['log'])
        open_result['log'] = [row for row in open_result['log'] if row['type'] != 'movement']
        mapped_result['log'] = [row for row in mapped_result['log'] if row['type'] != 'movement']
        require(open_result == mapped_result, f'contact_open_mismatch:{seed}')
        check_audits(mapped_duel, mapped_actual, (0, 1), 12)
    require(fast_uses > 0, 'contact_grid_did_not_exercise_fast')
    return {'cases': 50, 'fast_uses': fast_uses,
            'mro': [base.__name__ for base in mro]}


def baseline_class():
    commit = subprocess.check_output(
        ['git', '--no-replace-objects', 'rev-parse', f'{BASELINE_COMMIT}^{{commit}}'],
        cwd=ROOT, text=True).strip()
    source_bytes = subprocess.check_output(
        ['git', '--no-replace-objects', 'show',
         f'{commit}:experimental/corridor.py'],
        cwd=ROOT)
    source = source_bytes.decode('utf-8')
    scope = {'__name__': 'experimental.corridor_baseline',
             '__package__': 'experimental'}
    exec(compile(source, f'{commit}:experimental/corridor.py', 'exec'), scope)
    return scope['CorridorDuel'], commit, sha256(source_bytes).hexdigest()


def historical_replays() -> dict:
    old_class, commit, source_hash = baseline_class()
    hero, foe = blacklight_profile(), gunner()
    policies = (SHIELD_BLADE_HAMMER_REACTIVE, KITER)
    for seed in range(50):
        options = {'seed': seed, 'length': 12, 'initial_positions': (0, 8),
                   'max_rounds': 10, 'audit': True}
        before = old_class((hero, foe), policies, **options)
        after = CorridorDuel((hero, foe), policies, **options)
        before_result = before.run()
        after_result = after.run()
        require(before_result == after_result, f'historical_result_mismatch:{seed}')
        require((before.positions, before.wall_reached, before.contact_occurred) ==
                (after.positions, after.wall_reached, after.contact_occurred),
                f'historical_spatial_mismatch:{seed}')
        check_audits(after, after_result, (0, 8), 12)
    return {'cases': 50, 'baseline_commit': commit,
            'baseline_corridor_sha256': source_hash,
            'comparison_scope': 'Historical corridor class with current core and policies; geometry migration only'}


def mapped_grids() -> dict:
    hero = blacklight_profile()
    ammo = gunner()
    nonammo = replace(ammo, rank=4, ranged_is_ammunition=False)
    policy = SplitFastPolicy('blade_hammer', weapon='blade', offhand='hammer',
                             prefer_fast=True, effect_limb=1)
    counts = {}
    for length, foe in ((12, ammo), (20, nonammo)):
        key = f'L{length}_{"ammo" if foe.ranged_is_ammunition else "nonammo"}'
        fast_uses = walls = contacts = blocked_retreats = 0
        for seed in range(50):
            duel = SplitFastCorridorDuel(
                (hero, foe), (policy, KITER), seed=seed, length=length,
                initial_positions=(0, 8), max_rounds=10, audit=True)
            result = duel.run()
            check_audits(duel, result, (0, 8), length)
            fast_uses += sum(row['type'] == 'fast_use_start' for row in result.log)
            blocked_retreats += sum(row['type'] == 'movement' and
                                    row['direction'] == 'retreat' and
                                    row['actual_steps'] == 0 for row in result.log)
            walls += duel.wall_reached
            contacts += duel.contact_occurred
        require(fast_uses > 0 and walls > 0, f'mapped_grid_not_exercised:{key}')
        counts[key] = {'cases': 50, 'fast_uses': fast_uses,
                       'walls': walls, 'contacts': contacts,
                       'blocked_retreats': blocked_retreats}
    return counts


def terrain_and_wall() -> dict:
    hero = replace(blacklight_profile(), agility=5, agility_defense=15,
                   run_speed=6)
    foe = gunner()
    aware = WallAwarePolicy('same', kite=True, move_after_attack=True,
                            treat_bleeding=True, effect_limb=0)
    duel = SplitFastCorridorDuel(
        (hero, foe), (KITER, aware), seed=1,
        length=12, initial_positions=(11, 12), audit=True)
    observation = duel.observe(1)
    require(observation.terrain is not None and observation.terrain.me == (12, 0),
            'terrain_view_wrong_actor')
    require(KITER.choose_action(observation).kind == 'move' and
            aware.choose_action(observation).kind == 'ranged',
            'wall_fallback_failed')
    try:
        observation.terrain.me = (1, 0)
    except (AttributeError, TypeError):
        pass
    else:
        raise AssertionError('terrain_view_is_mutable')
    require(tuple(duel.positions) == (11, 12), 'observation_mutated_battle')
    duel.active_actor = 0
    duel.fighters[0].movement_available = True
    duel._move(0, Move('retreat', 1))
    require(observation.terrain.foe == (11, 0) and
            duel.observe(1).terrain.foe == (10, 0),
            'terrain_view_is_not_a_snapshot')
    return {'readonly_snapshot': True, 'run6_wall_fallback': True}


class ForcedRolls:
    def __init__(self, values: tuple[int, ...]):
        self.values = iter(values)

    def randint(self, low: int, high: int) -> int:
        value = next(self.values)
        require(low <= value <= high, 'forced_roll_out_of_range')
        return value


def attack_state(duel) -> tuple:
    return (tuple(f.health for f in duel.fighters),
            tuple((f.attacks, f.hits, f.fantastic_hits, f.damage_dealt,
                   f.damage_taken, f.damage_mitigated) for f in duel.fighters),
            duel.distance, tuple(duel.positions))


def knockback_boundary() -> dict:
    hero, foe = blacklight_profile(), gunner()
    policy = replace(HAMMER, edge_mode='decline')
    duel = SplitFastCorridorDuel(
        (hero, foe), (policy, KITER), seed=1,
        length=8, initial_positions=(7, 8), audit=True)
    duel.fighters[1].stance = True
    duel.rng = ForcedRolls((6, 1, 6))
    before = attack_state(duel)
    try:
        duel._attack(0, 'hammer')
    except NotImplementedError:
        pass
    else:
        raise AssertionError('positive_knockback_was_accepted')
    require(attack_state(duel) == before, 'positive_knockback_mutated_core_state')
    require(not any(row['type'] in ('attack', 'knockback') for row in duel.log),
            'positive_knockback_recorded_applied_effect')

    reduced = replace(foe, health_dr=100)
    zero = SplitFastCorridorDuel(
        (hero, reduced), (policy, KITER), seed=1,
        length=8, initial_positions=(7, 8), audit=True)
    zero.fighters[1].stance = True
    zero.rng = ForcedRolls((6, 1, 6))
    zero._attack(0, 'hammer')
    require(zero.fighters[0].attacks == 1 and zero.distance == 1 and
            zero.positions == [7, 8] and
            sum(row['type'] == 'attack' for row in zero.log) == 1 and
            not any(row['type'] == 'knockback' for row in zero.log),
            'zero_space_knockback_rejected_or_moved')
    return {'positive_rejected_before_core_state_change': True,
            'zero_space_accepted': True}


def geometry_consistency() -> dict:
    hero = blacklight_profile()
    foe = replace(hero, name='Unshielded Target', weapons=frozenset())
    policy = replace(HAMMER, edge_mode='decline')
    duel = SplitFastCorridorDuel(
        (hero, foe), (policy, policy), seed=1,
        length=8, initial_positions=(0, 1), audit=True)
    duel.rng = ForcedRolls((2, 5, 3))
    check = duel._prepare_attack_check(0, 'melee')
    require(check.result.success and not check.result.fantastic,
            'prepared_geometry_probe_roll_changed')
    duel.distance = 2  # Forge a desynchronization after check preparation.
    before = attack_state(duel)
    try:
        duel._attack(0, 'melee', prepared_check=check)
    except RuntimeError:
        pass
    else:
        raise AssertionError('prepared_check_bypassed_geometry_guard')
    require(attack_state(duel) == before and not duel.log,
            'geometry_guard_rejected_after_attack_mutation')

    mapped = SplitFastCorridorDuel(
        (hero, gunner()), (policy, KITER), seed=1,
        length=12, initial_positions=(0, 8), max_rounds=2, audit=True)
    result = mapped.run()
    altered = deepcopy(list(result.log))
    attack = next(row for row in altered if row['type'] == 'attack')
    attack['distance'] += 1
    issues = audit_corridor(altered, (hero.name, gunner().name),
                            initial_positions=(0, 8), length=12,
                            final_positions=tuple(mapped.positions))
    require(any('attack distance mismatch' in issue for issue in issues),
            'position_auditor_accepted_forged_attack_distance')
    return {'prepared_check_cannot_bypass_guard': True,
            'forged_attack_distance_rejected': True}


def runner_and_cli() -> dict:
    hero = load_sheet(ROOT / 'characters/victor_halle/rank3_2026-10-27_split_fast.json')
    foe = load_sheet(ROOT / 'characters/examples/synthetic_rank4_split_fast.json')
    old_hero = load_sheet(ROOT / 'characters/victor_halle/rank3_2026-10-26.json')
    old_foe = load_sheet(ROOT / 'characters/examples/synthetic_rank4.json')
    current = SplitFastPolicy('same', effect_limb=0)
    aware = WallAwarePolicy('same', effect_limb=0)
    require(asdict(current) == asdict(aware), 'policy_identity_case_not_comparable')
    battlefield = CorridorMap(12, (0, 1))
    duel = run_duel(hero, foe, current, aware, seed=3,
                    battlefield=battlefield, max_rounds=3)
    require(duel['execution_adapter'] == 'split_fast_corridor_v1' and
            duel['audit_issues'] == [] and
            duel['battlefield'] == battlefield.record() and
            duel['policy_types'][0] != duel['policy_types'][1],
            'runner_map_metadata_or_audit_failed')
    paths = {name.replace('\\', '/') for name in duel['source_sha256']}
    require({'experimental/corridor.py', 'experimental/corridor_audit.py',
             'combatants/battlefields.py', 'combatants/terrain_policies.py'} <= paths,
            'runner_map_sources_missing')
    for report in duel['coverage']:
        require('open field' not in report['scope_limits'],
                'mapped_coverage_claims_open_field')
    batch_plain = run_batch(hero, foe, current, current, n=1,
                            master_seed=9, max_rounds=1, battlefield=battlefield)
    batch_aware = run_batch(hero, foe, aware, current, n=1,
                            master_seed=9, max_rounds=1, battlefield=battlefield)
    require(batch_plain['policies'][0] == batch_aware['policies'][0] and
            batch_plain['cell_sha256'] != batch_aware['cell_sha256'],
            'current_policy_class_not_in_cell_identity')
    for batch in (batch_plain, batch_aware):
        key = f"character-batch-v2|9|{batch['cell_sha256']}|0"
        expected = int.from_bytes(sha256(key.encode()).digest()[:8], 'big')
        require(batch['audited_traces'][0]['seed'] == expected,
                'current_v2_seed_formula_mismatch')
    legacy = run_batch(old_hero, old_foe, ATTACK, ATTACK, n=1,
                       master_seed=9, max_rounds=1)
    old_cell = {name: legacy[name] for name in
                ('sheets', 'policies', 'initial_distance', 'max_rounds')}
    old_hash = sha256(json.dumps(old_cell, sort_keys=True,
                                 separators=(',', ':')).encode()).hexdigest()
    key = f"character-batch-v1|9|{legacy['cell_sha256']}|0"
    expected = int.from_bytes(sha256(key.encode()).digest()[:8], 'big')
    require(legacy['audited_traces'][0]['seed'] == expected and
            legacy['cell_sha256'] == old_hash,
            'historical_v1_seed_contract_changed')

    gunner_sheet = ROOT / 'characters/examples/synthetic_rank4_nonammo_gunner.json'
    with TemporaryDirectory(prefix='blacklight-corridor-audit-') as folder:
        temporary_root = Path(folder).resolve()
        if (not temporary_root.is_relative_to(Path(gettempdir()).resolve())
                or not temporary_root.name.startswith('blacklight-corridor-audit-')):
            raise AssertionError('Unexpected temporary audit path')
        output = temporary_root / 'smoke.json'
        command = [sys.executable, '-B', '-m', 'scripts.character_sheet', 'duel',
                   '--hero', str(ROOT / 'characters/victor_halle/rank3_2026-10-27_split_fast.json'),
                   '--opponent', str(gunner_sheet), '--policy', 'attack',
                   '--opponent-policy', 'kiter', '--corridor-length', '12',
                   '--positions', '0', '8', '--opponent-wall-aware',
                   '--seed', '3', '--output', str(output)]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True,
                                   text=True, check=False)
        require(completed.returncode == 0 and output.is_file(),
                f'cli_corridor_failed:{completed.stderr[-500:]}')
        payload = json.loads(output.read_text(encoding='utf-8'))
        require(payload['audit_issues'] == [] and
                payload['battlefield'] == CorridorMap(12, (0, 8)).record() and
                payload['policy_types'][1]['class'] == 'WallAwarePolicy' and
                any(name.replace('\\', '/') == 'scripts/character_sheet.py'
                    for name in payload['source_sha256']),
                'cli_corridor_output_mismatch')
    return {'runner_duel': True, 'current_v2_policy_seeds': True,
            'legacy_v1_seed': True, 'cli_temp_smoke': True}


def main() -> None:
    sources = audit_source_manifest()
    results = {'contact_open_equivalence': equivalent_contact(),
               'historical_replays': historical_replays(),
               'mapped_grids': mapped_grids(),
               'terrain_and_wall': terrain_and_wall(),
               'knockback_boundary': knockback_boundary(),
               'geometry_consistency': geometry_consistency(),
               'runner_and_cli': runner_and_cli()}
    require_audit_sources_unchanged(sources)
    results['source_sha256'] = sources
    print(json.dumps(results, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
