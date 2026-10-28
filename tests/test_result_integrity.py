"""A successful audit must bind the reported summary to the combat trace."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

from blacklight.engine import BattleResult, Duel, Profile
from blacklight.batch_audit import audit_batch_metadata
from blacklight.policies import ATTACK
from blacklight.result_audit import audit_battle_result
from blacklight.spatial_audit import audit_open_field_distance
from blacklight.turn_audit import audit_turn_sequence
from combatants.duel_adapter import compile_duel
from combatants.runner import run_batch, run_duel
from combatants.sheets import load_sheet
from combatants.split_fast import SplitFastDuel


ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / 'characters/victor_halle/rank3_2026-10-27_split_fast.json'
FOE = ROOT / 'characters/examples/synthetic_rank4_split_fast.json'


class TestResultIntegrity(unittest.TestCase):
    def setUp(self):
        self.hero, self.foe = load_sheet(HERO), load_sheet(FOE)

    def test_wrong_winner_final_resources_and_metrics_are_rejected(self):
        original = SplitFastDuel._finish

        def fake_summary(field):
            def fake(battle, *args):
                result = original(battle, *args)
                if field == 'winner':
                    return replace(result, outcome='win', winner='Fabricated Winner')
                if field == 'health':
                    return replace(result, final_health=(result.final_health[0] + 1, result.final_health[1]))
                if field == 'focus':
                    return replace(result, final_focus=(result.final_focus[0] + 1, result.final_focus[1]))
                metrics = deepcopy(result.metrics)
                metrics[0]['damage_dealt'] += 1
                return replace(result, metrics=metrics)
            return fake

        for field in ('winner', 'health', 'focus', 'metrics'):
            with self.subTest(field=field), patch.object(SplitFastDuel, '_finish', fake_summary(field)):
                with self.assertRaisesRegex(RuntimeError, 'result.*(mismatch|inconsistent)'):
                    run_duel(self.hero, self.foe, ATTACK, ATTACK, seed=51, max_rounds=3)

    def test_corrupt_open_field_distance_is_rejected_by_runner(self):
        original = Duel._move

        def fake_move(battle, *args, **kwargs):
            before = len(battle.log)
            result = original(battle, *args, **kwargs)
            if len(battle.log) > before and battle.log[-1]['type'] == 'movement':
                battle.log[-1]['distance_after'] = 99
            return result

        with patch.object(Duel, '_move', fake_move):
            with self.assertRaisesRegex(RuntimeError, 'distance'):
                run_duel(self.hero, self.foe, ATTACK, ATTACK, seed=51,
                         initial_distance=3, max_rounds=3)

    def test_action_outside_turn_and_changed_initiative_order_are_rejected(self):
        profiles = tuple(map(compile_duel, (self.hero, self.foe)))
        policy = replace(ATTACK, always_wait=True, riposte=False)
        original = SplitFastDuel._finish

        def after_turn(battle, *args):
            result = original(battle, *args)
            events = deepcopy(list(result.log))
            index = next(i for i, e in enumerate(events) if e['type'] == 'wait')
            event = events.pop(index)
            end = next(i for i, e in enumerate(events)
                       if e['type'] == 'turn_end' and e['actor'] == event['actor'])
            events.insert(end + 1, event)
            for seq, row in enumerate(events, 1):
                row['seq'] = seq
            return replace(result, log=tuple(events))

        with patch.object(SplitFastDuel, '_finish', after_turn):
            with self.assertRaisesRegex(RuntimeError, 'action outside the actor turn'):
                run_duel(self.hero, self.foe, policy, policy, seed=1, max_rounds=1)

        result = SplitFastDuel(profiles, (policy, policy), seed=1, max_rounds=1, audit=True).run()
        events = deepcopy(list(result.log))
        turn_starts = [e for e in events if e['type'] == 'turn_start']
        self.assertEqual(len(turn_starts), 2)
        turn_starts[0]['actor'], turn_starts[1]['actor'] = turn_starts[1]['actor'], turn_starts[0]['actor']
        self.assertTrue(any('initiative' in issue for issue in
                            audit_turn_sequence(events, profiles, outcome=result.outcome)))

    def test_partial_batch_is_explicitly_distinguished_from_auditing_every_fight(self):
        full = run_batch(self.hero, self.foe, ATTACK, ATTACK, n=3, master_seed=51, max_rounds=2)
        partial = run_batch(self.hero, self.foe, ATTACK, ATTACK, n=3, master_seed=51,
                            max_rounds=2, audit_every=2)
        self.assertEqual((full['audit_scope'], len(full['audited_traces'])), ('all_starts', 3))
        self.assertEqual((partial['audit_scope'], len(partial['audited_traces'])), ('sampled_starts', 2))
        self.assertEqual((full['outcomes'], full['metrics_all_starts']),
                         (partial['outcomes'], partial['metrics_all_starts']))
        self.assertEqual(audit_batch_metadata(full), [])
        self.assertTrue(audit_batch_metadata(partial))
        for field in ('seed', 'index', 'issues', 'cell', 'rate', 'outcome'):
            forged = deepcopy(full)
            if field in ('seed', 'index'):
                forged['audited_traces'][1][field] += 1
            elif field == 'issues':
                forged['audited_traces'][1]['issues'] = ['forged error']
            elif field == 'cell':
                forged['cell_sha256'] = '0' * 64
            elif field == 'rate':
                forged['rates']['win']['estimate'] += 0.1
            else:
                forged['outcomes']['win'] += 1
            with self.subTest(field=field):
                self.assertTrue(audit_batch_metadata(forged))
        for count, interval in ((True, 1), (1, True), (1, 0), (0, 1)):
            with self.subTest(n=count, audit_every=interval):
                with self.assertRaises(ValueError):
                    run_batch(self.hero, self.foe, ATTACK, ATTACK, n=count,
                              master_seed=1, audit_every=interval)
        for invalid_seed in (True, 1.5, '1'):
            with self.subTest(seed=invalid_seed):
                with self.assertRaisesRegex(ValueError, 'seed'):
                    run_duel(self.hero, self.foe, ATTACK, ATTACK, seed=invalid_seed)
                with self.assertRaises(ValueError):
                    run_batch(self.hero, self.foe, ATTACK, ATTACK, n=1,
                              master_seed=invalid_seed)

    def test_manual_distance_and_knockback_oracle(self):
        log = [
            {'seq': 1, 'type': 'movement', 'direction': 'approach', 'steps': 5,
             'distance_before': 8, 'distance_after': 3},
            {'seq': 2, 'type': 'attack', 'distance': 3},
            {'seq': 3, 'type': 'movement', 'direction': 'approach', 'steps': 5,
             'distance_before': 3, 'distance_after': 1},
            {'seq': 4, 'type': 'knockback', 'spaces': 10,
             'distance_before': 1, 'distance_after': 11},
            {'seq': 5, 'type': 'attack', 'distance': 11},
        ]
        self.assertEqual(audit_open_field_distance(log, 8), [])
        for index, field in ((0, 'distance_after'), (2, 'distance_before'),
                             (3, 'spaces'), (4, 'distance')):
            forged = deepcopy(log)
            forged[index][field] += 1
            with self.subTest(index=index, field=field):
                self.assertTrue(audit_open_field_distance(forged, 8))

    def test_manual_result_summary_oracle(self):
        first = Profile('A', 1, 100, 50, 2, 0, 1, 0, 12, 10, 5)
        second = replace(first, name='B')
        log = (
            {'seq': 1, 'round': 0, 'bonus_round': False, 'type': 'initiative', 'actor': 'A',
             'total': 12, 'modifier': 1, 'fantastic': False},
            {'seq': 2, 'round': 0, 'bonus_round': False, 'type': 'initiative', 'actor': 'B',
             'total': 10, 'modifier': 1, 'fantastic': False},
            {'seq': 3, 'round': 1, 'bonus_round': False, 'type': 'turn_start', 'actor': 'A'},
            {'seq': 4, 'round': 1, 'bonus_round': False, 'type': 'attack', 'actor': 'A', 'target': 'B',
             'damage': 10, 'calculated_damage': 10, 'health_after': 90,
             'success': True, 'fantastic': False, 'reaction': False,
             'damage_components': [{'damage_without_reduction': 14}]},
            {'seq': 5, 'round': 1, 'bonus_round': False, 'type': 'turn_end', 'actor': 'A'},
            {'seq': 6, 'round': 1, 'bonus_round': False, 'type': 'turn_start', 'actor': 'B'},
            {'seq': 7, 'round': 1, 'bonus_round': False, 'type': 'turn_end', 'actor': 'B'},
        )
        zero = dict.fromkeys(('damage_dealt', 'damage_taken', 'damage_mitigated', 'healing_effective',
                              'focus_spent', 'attacks', 'hits', 'fantastic_hits', 'ripostes',
                              'stuns_applied', 'blade_bonus_actions', 'damage_round3', 'damage_round5',
                              'damage_round10'), 0)
        attack = {**zero, 'damage_dealt': 10, 'attacks': 1, 'hits': 1,
                  'damage_round3': 10, 'damage_round5': 10, 'damage_round10': 10}
        defense = {**zero, 'damage_taken': 10, 'damage_mitigated': 4}
        result = BattleResult(7, None, 'inconclusive', 1, 2, False,
                              (100, 90), (50, 50), (attack, defense), log)
        self.assertEqual(audit_battle_result(result, (first, second), expected_seed=7, max_rounds=1), [])
        altered = replace(result, winner='A', outcome='win')
        self.assertTrue(any('winner' in issue for issue in
                            audit_battle_result(altered, (first, second), expected_seed=7, max_rounds=1)))


if __name__ == '__main__':
    unittest.main()
