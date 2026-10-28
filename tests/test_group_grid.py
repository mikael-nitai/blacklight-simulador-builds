"""Forced geometry cases and independent audit of experimental group grid."""

from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import unittest

from blacklight.engine import IllegalAction, Profile, ReactionEvent, blacklight_profile
from combatants.duel_adapter import compile_duel
from combatants.group_grid import (GridGroupBattle, GridGroupPolicy, GridMove,
                                   GroupGrid, grid_distance, supported_sight)
from combatants.group_grid_audit import audit_group_grid
from combatants.group_runner import GRID_SCHEMA, run_group
from combatants.sheets import load_sheet
from combatants.split_fast import FastAction
from scripts.freeze_results import require_generic_provenance


class Dice:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        return next(self.values)


def setup(positions=((0, 0), (1, 0), (0, 1)), *, width=10, height=10):
    hero = replace(blacklight_profile(), heroic=False)
    enemy = Profile('A', 3, 1000, 90, 4, 2, 3, 2, 14, 12, 5,
                    powers=frozenset({'riposte'}))
    profiles = (hero, enemy, replace(enemy, name='B'))
    policy = GridGroupPolicy('hero', weapon='hammer', offhand='blade', prefer_fast=True,
                             split_targets=True, edge_mode='decline', riposte=False)
    opponent = GridGroupPolicy('enemy', edge_mode='decline', riposte=True)
    grid = GroupGrid(width, height, positions)
    game = GridGroupBattle(profiles, (policy, opponent, opponent), grid=grid,
                           teams=('hero', 'enemies', 'enemies'), seed=1, audit=True)
    game.round = 1
    game._reset_reactions_for_round()
    game.active_actor = 0
    game.fighters[0].standard_available = game.fighters[0].movement_available = True
    return game, profiles


class TestGroupGrid(unittest.TestCase):
    def test_layout_and_diagonal_distance(self):
        grid = GroupGrid(5, 5, ((0, 0), (4, 3), (1, 2)))
        self.assertEqual(grid_distance((0, 0), (4, 3)), 4)
        with self.assertRaises(FrozenInstanceError):
            grid.width = 8
        for positions in (((0, 0), (0, 0)), ((0, 0), (1, True)), ((0, 0), (5, 1))):
            with self.assertRaises(ValueError):
                GroupGrid(5, 5, positions)
        self.assertTrue(supported_sight((0, 0), (3, 3), {(0, 0), (3, 3)}))
        self.assertFalse(supported_sight((0, 0), (3, 3), {(1, 1)}))
        self.assertFalse(supported_sight((0, 0), (3, 2), set()))
        self.assertFalse(supported_sight((0, 0), (201, 0), set()))

    def test_movement_validates_entire_path_before_spending(self):
        game, _ = setup(positions=((0, 0), (1, 0), (7, 7)))
        for path in (((1, 0),), ((0, 1), (2, 2)), ((-1, 0),)):
            with self.assertRaises(IllegalAction):
                game._move(0, GridMove(path))
            self.assertEqual(game.positions[0], (0, 0))
            self.assertTrue(game.fighters[0].movement_available)
        game._move(0, GridMove(((0, 1), (1, 2), (2, 2))))
        self.assertEqual(game.positions[0], (2, 2))
        self.assertFalse(game.fighters[0].movement_available)

    def test_fast_requires_both_targets_in_reach_before_spending_or_shield(self):
        game, _ = setup(positions=((0, 0), (1, 0), (5, 5)))
        game.fighters[0].shield_active = True
        before = len(game.log)
        game.rng = Dice([])
        with self.assertRaises(IllegalAction):
            game._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=0, targets=(1, 2)))
        self.assertTrue(game.fighters[0].shield_active)
        self.assertTrue(game.fighters[0].standard_available)
        self.assertEqual(len(game.log), before)

    def test_two_adjacent_targets_have_independent_damage_and_effects(self):
        game, _ = setup()
        game.rng = Dice((2, 1, 2, 6, 6, 6))
        game.damage_rng = Dice([1] * 100)
        game._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=0, targets=(1, 2)))
        self.assertEqual((game.fighters[1].health, game.fighters[2].health), (946, 979))
        self.assertEqual((game.fighters[1].stunned_by, game.fighters[2].bleeding), (0, 0))
        self.assertEqual([e['distance'] for e in game.log if e['type'] == 'attack'], [1, 1])

    def test_prepared_check_cannot_bypass_changed_range(self):
        game, _ = setup()
        game.rng = Dice((6, 6, 6))
        check = game._prepare_attack_check(0, 'hammer', target_actor=1)
        game.positions[1] = (6, 6)
        before = game.fighters[1].health
        with self.assertRaises(IllegalAction):
            game._attack(0, 'hammer', target_actor=1, prepared_check=check)
        self.assertEqual(game.fighters[1].health, before)

    def test_ranged_normal_long_and_blocked_sight(self):
        shooter = Profile('Shooter', 3, 100, 90, 2, 4, 3, 2, 12, 14, 5, ranged_range=3)
        target = Profile('Target', 3, 100, 90, 2, 2, 3, 2, 12, 12, 5)
        other = replace(target, name='Other')
        policies = (GridGroupPolicy('shoot'), GridGroupPolicy('x'), GridGroupPolicy('y'))
        for x, trouble in ((3, 0), (6, 1)):
            game = GridGroupBattle((shooter, target, other), policies,
                                   grid=GroupGrid(9, 3, ((0, 0), (x, 0), (0, 2))),
                                   teams=('a', 'b', 'b'), seed=1)
            self.assertEqual(game._attack_check_spec(0, 'ranged', 1).troubles, trouble)
        for positions in (((0, 0), (7, 0), (0, 2)), ((0, 0), (3, 0), (1, 0)),
                          ((0, 0), (3, 2), (0, 2))):
            game = GridGroupBattle((shooter, target, other), policies,
                                   grid=GroupGrid(9, 3, positions), teams=('a', 'b', 'b'), seed=1)
            with self.assertRaises(IllegalAction):
                game._attack_check_spec(0, 'ranged', 1)

    def test_out_of_reach_reaction_targets_actual_source(self):
        game, _ = setup(positions=((0, 0), (1, 0), (5, 5)))
        game.pending.append(ReactionEvent('riposte', 2, 0, 9))
        game.rng = Dice([])
        game._drain_events()
        self.assertEqual(game.fighters[2].ripostes, 0)
        self.assertEqual(game.fighters[2].reactions, 1)

    def test_grid_audit_reconstructs_long_range_trouble(self):
        shooter = Profile('Shooter', 3, 100, 90, 2, 4, 3, 2, 12, 14, 5, ranged_range=3)
        target = Profile('Target', 3, 100, 90, 2, 2, 3, 2, 12, 12, 5)
        profiles = (shooter, target, replace(target, name='Other'))
        positions = ((0, 0), (6, 0), (0, 2))
        policy = GridGroupPolicy('control', edge_mode='decline')
        game = GridGroupBattle(profiles, (policy,) * 3, grid=GroupGrid(9, 3, positions),
                               teams=('a', 'b', 'b'), seed=1, audit=True)
        game.rng = Dice((6, 6, 6, 2))
        game.damage_rng = Dice([6] * 20)
        game._attack(0, 'ranged', target_actor=1)
        self.assertEqual(audit_group_grid(game.log, profiles, width=9, height=3,
                                         initial_positions=positions, final_positions=positions), [])
        rows = deepcopy(game.log)
        for row in rows:
            if row['type'] in ('group_hit_check', 'attack'):
                row['troubles'] = 0
        self.assertTrue(any('incorrect ranged trouble' in issue for issue in
                            audit_group_grid(rows, profiles, width=9, height=3,
                                             initial_positions=positions, final_positions=positions)))

    def test_policy_chooses_reachable_target_over_wounded_distant_enemy(self):
        game, _ = setup(positions=((0, 0), (1, 1), (5, 5)))
        game.fighters[2].health = 1
        action = game.policies[0].choose_action(game.observe(0))
        self.assertEqual(action.targets, (1, 1))
        self.assertIn(action, game.legal_actions(0))

    def test_full_sheet_runner_and_independent_position_audit(self):
        hero = load_sheet('characters/victor_halle/rank3_2026-10-27_split_fast.json')
        sheets = (hero, replace(hero, name='A'), replace(hero, name='B'))
        policies = (GridGroupPolicy('h', weapon='hammer', offhand='blade', prefer_fast=True,
                                    split_targets=True), GridGroupPolicy('a'), GridGroupPolicy('b'))
        grid = GroupGrid(15, 10, ((1, 1), (13, 1), (13, 8)))
        kwargs = dict(grid=grid, teams=('h', 'e', 'e'), initiative_roles=('player', 'npc', 'npc'),
                      initiative_tie_order=(0, 1, 2), seed=2, max_rounds=10)
        record = run_group(sheets, policies, **kwargs)
        self.assertEqual(record, run_group(sheets, policies, **kwargs))
        self.assertEqual(record['schema'], GRID_SCHEMA)
        self.assertEqual(record['audit_issues'], [])
        self.assertTrue(any(row['type'] == 'group_grid_move' and row['steps'] > 0
                            for row in record['result']['log']))
        profiles = tuple(compile_duel(sheet) for sheet in sheets)
        rows = deepcopy(record['result']['log'])
        move = next(row for row in rows if row['type'] == 'group_grid_move' and row['steps'] > 0)
        move['path'][0] = [14, 9]
        issues = audit_group_grid(rows, profiles, width=grid.width, height=grid.height,
                                  initial_positions=grid.initial_positions,
                                  final_positions=record['result']['final_positions'])
        self.assertTrue(any('nonadjacent' in issue for issue in issues))
        rows = deepcopy(record['result']['log'])
        next(row for row in rows if row['type'] == 'attack')['distance'] = 99
        self.assertTrue(any('distance disagrees' in issue for issue in
                            audit_group_grid(rows, profiles, width=grid.width, height=grid.height,
                                             initial_positions=grid.initial_positions,
                                             final_positions=record['result']['final_positions'])))
        with self.assertRaisesRegex(ValueError, 'Experimental group'):
            require_generic_provenance(record, Path('.'), 'unused')

    def test_auditor_rejects_boolean_or_overlapping_final_positions(self):
        game, profiles = setup(positions=((1, 1), (5, 1), (5, 5)))
        for final in (((True, True), (5, 1), (5, 5)), ((1, 1), (5, 1), (5, 1))):
            with self.subTest(final=final), self.assertRaises(ValueError):
                audit_group_grid([], profiles, width=10, height=10,
                                 initial_positions=((1, 1), (5, 1), (5, 5)),
                                 final_positions=final)
        forged = [{'seq': 1, 'round': 1, 'bonus_round': False, 'type': 'group_grid_move',
                   'actor': 'Blacklight', 'origin': [True, True], 'destination': [True, True],
                   'path': [], 'steps': 0, 'as_standard': False}]
        self.assertTrue(any('invalid grid path' in issue for issue in
                            audit_group_grid(forged, profiles, width=10, height=10,
                                             initial_positions=((1, 1), (5, 1), (5, 5)),
                                             final_positions=((1, 1), (5, 1), (5, 5)))))


if __name__ == '__main__':
    unittest.main()
