"""Independent geometry and current-table integration gates for two sheets."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, asdict, replace
from hashlib import sha256
import json
from pathlib import Path
import unittest

from blacklight.audit import audit_log
from blacklight.engine import Action, IllegalAction, Move, Profile, blacklight_profile
from blacklight.policies import ATTACK, KITER, RulePolicy
from combatants import compile_duel, load_sheet
from combatants.battlefields import CorridorMap
from combatants.runner import run_batch, run_duel
from combatants.split_fast import FastAction, SplitFastDuel, SplitFastPolicy
from combatants.terrain_policies import WallAwarePolicy
from experimental.corridor import CorridorDuel, SplitFastCorridorDuel
from experimental.corridor_audit import audit_corridor


ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / 'characters/victor_halle/rank3_2026-10-27_split_fast.json'
FOE = ROOT / 'characters/examples/synthetic_rank4_nonammo_gunner.json'


class Dice:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        value = next(self.values)
        assert low <= value <= high
        return value


def policy(effect=0):
    return SplitFastPolicy('control', weapon='hammer', offhand='blade', prefer_fast=True,
                            effect_limb=effect, edge_mode='decline', riposte=False)


def game(*, positions=(0, 8), length=12, foe=None):
    target = foe or compile_duel(load_sheet(FOE))
    duel = SplitFastCorridorDuel((blacklight_profile(), target), (policy(), ATTACK),
                                 seed=1, length=length, initial_positions=positions, audit=True)
    duel.round = 1
    return duel


class TestCurrentCorridor(unittest.TestCase):
    def test_layout_is_immutable_and_rejects_fractional_or_overlapping_cells(self):
        layout = CorridorMap(12, (0, 8))
        self.assertEqual(layout.distance, 8)
        record = layout.record()
        record['initial_positions'][0] = 3
        self.assertEqual(layout.initial_positions, (0, 8))
        with self.assertRaises(FrozenInstanceError):
            layout.length = 20
        for length, positions in ((12.0, (0, 8)), (True, (0, 1)), (8, (0, 8.0)),
                                  (8, (False, 8)), (8, [0, 8]), (8, (8, 8)),
                                  (8, (9, 10)), (8, (2, 1))):
            with self.assertRaises(ValueError):
                CorridorMap(length, positions)

    def test_integer_movement_oracles_and_action_costs(self):
        cases = ((0, (0, 8), 'approach', 5, (5, 8)),
                 (0, (5, 8), 'approach', 5, (7, 8)),
                 (0, (1, 8), 'retreat', 5, (0, 8)),
                 (1, (0, 8), 'retreat', 6, (0, 12)),
                 (1, (7, 12), 'approach', 6, (7, 8)),
                 (1, (0, 12), 'retreat', 6, (0, 12)))
        for actor, initial, direction, steps, expected in cases:
            for standard in (False, True):
                duel = game(positions=initial)
                duel.active_actor = actor
                fighter = duel.fighters[actor]
                fighter.standard_available = fighter.movement_available = True
                duel._move(actor, Move(direction, steps), as_standard=standard)
                self.assertEqual(tuple(duel.positions), expected)
                self.assertEqual(duel.distance, expected[1] - expected[0])
                self.assertEqual((fighter.standard_available, fighter.movement_available),
                                 (False, True) if standard else (True, False))

    def test_bad_movement_cannot_mutate_positions_or_spend_action(self):
        for steps in (1.5, True, -1, 6):
            duel = game()
            duel.active_actor = 0
            fighter = duel.fighters[0]
            fighter.standard_available = fighter.movement_available = True
            with self.assertRaises(IllegalAction):
                duel._move(0, Move('approach', steps), as_standard=True)
            self.assertEqual(duel.positions, [0, 8])
            self.assertTrue(fighter.standard_available)
            self.assertTrue(fighter.movement_available)
            self.assertEqual(duel.log, [])

    def test_terrain_observation_is_detached_from_mutable_positions(self):
        duel = game()
        before = duel.observe(0)
        self.assertEqual((before.terrain.me, before.terrain.foe, before.terrain.size),
                         ((0, 0), (8, 0), (13, 1)))
        duel.active_actor = 0
        duel.fighters[0].movement_available = True
        duel._move(0, Move('approach', 5))
        self.assertEqual(before.terrain.me, (0, 0))
        self.assertEqual(duel.observe(0).terrain.me, (5, 0))
        with self.assertRaises(FrozenInstanceError):
            before.terrain.me = (2, 0)

    def test_inconsistent_internal_geometry_stops_before_a_check(self):
        duel = game()
        duel.positions = [5, 8]
        duel.rng = Dice([])
        with self.assertRaisesRegex(RuntimeError, 'inconsistent'):
            duel._attack(0, 'hammer')
        self.assertEqual(duel.fighters[1].health, duel.fighters[1].profile.max_health)
        self.assertEqual(duel.log, [])

    def test_two_prepared_checks_and_effects_cross_the_geometry_hook(self):
        target = replace(compile_duel(load_sheet(FOE)), max_health=1000)
        duel = game(positions=(7, 8), length=8, foe=target)
        duel._reset_reactions_for_round()
        duel.active_actor = 0
        duel.fighters[0].standard_available = True
        duel.rng, duel.damage_rng = Dice([2, 1, 2, 1, 2, 1]), Dice([1] * 100)
        duel._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=0))
        attacks = [e for e in duel.log if e['type'] == 'attack']
        self.assertEqual([e['success'] for e in attacks], [True, False])
        self.assertEqual([e['distance'] for e in attacks], [1, 1])
        self.assertEqual(duel.positions, [7, 8])
        self.assertEqual(duel.fighters[1].stunned_by, 0)
        self.assertTrue(issubclass(SplitFastCorridorDuel, SplitFastDuel))
        self.assertEqual(audit_log(duel.log,
                                   {f.profile.name: f.profile.max_health for f in duel.fighters},
                                   {f.profile.name: f.profile.max_focus for f in duel.fighters}), [])
        self.assertEqual(audit_corridor(duel.log, tuple(f.profile.name for f in duel.fighters),
                                        initial_positions=(7, 8), length=8,
                                        final_positions=tuple(duel.positions)), [])

    def test_knockback_gate_preserves_health_stats_and_geometry(self):
        target = replace(compile_duel(load_sheet(FOE)), max_health=1000)
        duel = game(positions=(7, 8), length=8, foe=target)
        duel.policies = (replace(ATTACK, weapon='hammer', edge_mode='decline'), ATTACK)
        duel.fighters[1].stance = True
        duel.rng, duel.damage_rng = Dice([6, 1, 6]), Dice([])
        fields = ('health', 'attacks', 'hits', 'fantastic_hits', 'damage_dealt',
                  'damage_taken', 'damage_mitigated')
        before = [tuple(getattr(fighter, name) for name in fields) for fighter in duel.fighters]
        with self.assertRaisesRegex(NotImplementedError, 'damage was not applied'):
            duel._attack(0, 'hammer')
        self.assertEqual([tuple(getattr(f, name) for name in fields) for f in duel.fighters], before)
        self.assertEqual((duel.positions, duel.distance), ([7, 8], 1))
        self.assertEqual(duel.log, [])

    def test_zero_distance_knockback_is_not_an_unmodeled_displacement(self):
        target = replace(compile_duel(load_sheet(FOE)), max_health=1000, health_dr=8)
        duel = game(positions=(7, 8), length=8, foe=target)
        duel.policies = (replace(ATTACK, weapon='hammer', edge_mode='decline'), ATTACK)
        duel.fighters[1].stance = True
        duel.rng, duel.damage_rng = Dice([6, 1, 6]), Dice([1] * 8)
        duel._attack(0, 'hammer')
        self.assertEqual((duel.positions, duel.distance, duel.fighters[1].health), ([7, 8], 1, 1000))

    def test_wall_aware_policy_shoots_instead_of_spending_a_blocked_standard(self):
        hunter = Profile('Hunter', 4, 150, 60, 6, 5, 5, 2, 16, 15, 6)
        gunner = compile_duel(load_sheet(FOE))
        aware = WallAwarePolicy(**asdict(KITER), effect_limb=0)
        results = []
        for defender_policy in (SplitFastPolicy(**asdict(KITER), effect_limb=0), aware):
            duel = SplitFastCorridorDuel((hunter, gunner), (ATTACK, defender_policy),
                                         seed=1, length=12, initial_positions=(11, 12), audit=True)
            duel.active_actor = 1
            duel.fighters[1].standard_available = duel.fighters[1].movement_available = True
            duel.rng, duel.damage_rng = Dice([6, 6, 6]), Dice([1] * 10)
            request = defender_policy.choose_action(duel.observe(1))
            duel._act(1, request)
            results.append((request.kind, duel.fighters[1].attacks, duel.fighters[0].health))
        self.assertEqual(results, [('move', 0, 150), ('ranged', 1, 120)])

    def test_generic_runner_derives_distance_and_reports_mapped_scope(self):
        result = run_duel(load_sheet(HERO), load_sheet(FOE), policy(),
                           WallAwarePolicy(**asdict(KITER), effect_limb=0),
                           seed=11, max_rounds=8, battlefield=CorridorMap(12))
        self.assertEqual(result['execution_adapter'], 'split_fast_corridor_v1')
        self.assertEqual(result['initial_distance'], 8)
        self.assertEqual(result['battlefield']['initial_positions'], [0, 8])
        self.assertEqual(result['audit_issues'], [])
        for report in result['coverage']:
            self.assertEqual(report['engine'], 'split_fast_corridor_v1')
            self.assertNotIn('open field', report['scope_limits'])
        for source in ('experimental/corridor.py', 'experimental/corridor_audit.py'):
            self.assertEqual(result['source_sha256'][Path(source).as_posix()],
                             sha256((ROOT / source).read_bytes()).hexdigest())

    def test_incompatible_map_inputs_fail_before_execution(self):
        hero, foe = load_sheet(HERO), load_sheet(FOE)
        for battlefield, distance in (({}, None), (False, None), (CorridorMap(12), 1)):
            with self.assertRaises(ValueError):
                run_duel(hero, foe, ATTACK, ATTACK, seed=1,
                           battlefield=battlefield, initial_distance=distance)

    def test_policy_type_and_map_are_part_of_current_seed_identity(self):
        hero, foe = load_sheet(HERO), load_sheet(FOE)
        regular, aware = SplitFastPolicy('same'), WallAwarePolicy('same')
        self.assertEqual(asdict(regular), asdict(aware))
        args = dict(n=2, master_seed=42, max_rounds=2, audit_every=1)
        a = run_batch(hero, foe, regular, ATTACK, battlefield=CorridorMap(12), **args)
        b = run_batch(hero, foe, aware, ATTACK, battlefield=CorridorMap(12), **args)
        c = run_batch(hero, foe, regular, ATTACK, battlefield=CorridorMap(20), **args)
        self.assertNotEqual(a['cell_sha256'], b['cell_sha256'])
        self.assertNotEqual(a['cell_sha256'], c['cell_sha256'])
        self.assertNotEqual(a['audited_traces'][0]['seed'], b['audited_traces'][0]['seed'])
        self.assertIn('character-batch-v2', a['seed_formula'])
        self.assertEqual(sum(a['outcomes'].values()), 2)
        self.assertTrue(all(0 <= value <= 2 for value in a['spatial_counts_all_starts'].values()))

    def test_legacy_cell_seed_is_preserved(self):
        stored = json.loads((ROOT / 'results/generic_sheet_rank4_batch.json').read_text(encoding='utf-8'))
        from combatants.sheets import parse_sheet
        hero, foe = (parse_sheet(data) for data in stored['sheets'])
        policies = tuple(RulePolicy(**data) for data in stored['policies'])
        result = run_batch(hero, foe, *policies, n=2, master_seed=stored['master_seed'],
                            initial_distance=stored['initial_distance'], max_rounds=stored['max_rounds'],
                            audit_every=1)
        self.assertIn('character-batch-v1', result['seed_formula'])
        self.assertEqual(result['cell_sha256'], stored['cell_sha256'])
        self.assertEqual(result['audited_traces'][0]['seed'], stored['audited_traces'][0]['seed'])

    def test_fractional_position_trace_is_rejected(self):
        duel = game()
        duel.active_actor = 0
        duel.fighters[0].movement_available = True
        duel._move(0, Move('approach', 5))
        changed = deepcopy(duel.log)
        changed[0]['steps'] = 5.0
        self.assertTrue(any('integer' in issue for issue in audit_corridor(
            changed, tuple(f.profile.name for f in duel.fighters), initial_positions=(0, 8),
            length=12, final_positions=(5, 8))))

    def test_prepared_check_cannot_bypass_position_consistency(self):
        duel = game(positions=(0, 1))
        duel.rng, duel.damage_rng = Dice([6, 6, 6]), Dice([])
        prepared = duel._prepare_attack_check(0, 'melee')
        duel.distance = 2
        before = duel.fighters[1].health
        with self.assertRaisesRegex(RuntimeError, 'inconsistent'):
            duel._attack(0, 'melee', prepared_check=prepared)
        self.assertEqual(duel.fighters[1].health, before)
        self.assertEqual(duel.log, [])


if __name__ == '__main__':
    unittest.main()
