"""Independent timing cases, including different owners and fallback boundaries."""

from dataclasses import FrozenInstanceError, asdict, replace
from itertools import product
import json
from pathlib import Path
import unittest

from blacklight.engine import Duel, Profile
from blacklight.policies import ATTACK, RulePolicy
from combatants.duel_adapter import compile_duel
from combatants.lifecycle import Boundary, TimePoint, TimedEffect, expiration_plan
from combatants.modular_duel import ModularDuel
from combatants.sheets import parse_sheet
from scripts.verify_sources import verify_result


def effect(token='a', *, kind='stunned', subject=0, source=1, deadlines=None):
    if deadlines is None:
        deadlines = (TimePoint(Boundary.TURN_START, 3, 1),)
    return TimedEffect(token, kind, subject, source, deadlines, ('TEST-ONLY',))


def battle(cls):
    profiles = tuple(Profile(name, 3, 90, 60, 4, 2, 3, 2, 14, 12, 5)
                     for name in ('A', 'B'))
    wait = replace(ATTACK, always_wait=True)
    game = cls(profiles, (wait, wait), seed=8, audit=True)
    game.round = 1
    return game


class TestLifecycle(unittest.TestCase):
    def test_next_source_turn_expires_but_subject_turn_does_not(self):
        pending = (effect(),)
        for actor, count, expected in ((0, 3, False), (1, 2, False),
                                       (1, 3, True), (1, 4, True)):
            result = expiration_plan(pending, TimePoint(Boundary.TURN_START, count, actor))
            self.assertEqual(bool(result.expired), expected)
            self.assertEqual(result.remaining, () if expected else pending)

    def test_start_end_and_round_clocks_remain_separate(self):
        pending = (effect(),)
        for boundary in (Boundary.TURN_END, Boundary.ROUND_START, Boundary.ROUND_END):
            actor = 1 if boundary == Boundary.TURN_END else None
            result = expiration_plan(pending, TimePoint(boundary, 20, actor))
            self.assertEqual(result.remaining, pending)

    def test_alternative_deadline_handles_source_missing_its_next_turn(self):
        # Generic timing fixture. Round fallback is not yet wired into Duel.
        pending = (effect(deadlines=(TimePoint(Boundary.TURN_START, 3, 1),
                                    TimePoint(Boundary.ROUND_END, 5))),)
        self.assertFalse(expiration_plan(pending, TimePoint(Boundary.ROUND_END, 4)).expired)
        self.assertEqual(expiration_plan(pending, TimePoint(Boundary.ROUND_END, 5)).expired,
                         pending)
        self.assertEqual(expiration_plan(pending, TimePoint(Boundary.TURN_START, 3, 1)).expired,
                         pending)

    def test_indefinite_effect_is_not_given_an_invented_duration(self):
        pending = (effect(deadlines=(), source=None),)
        for boundary in Boundary:
            now = TimePoint(boundary, 1000,
                            1 if boundary in (Boundary.TURN_START, Boundary.TURN_END) else None)
            self.assertEqual(expiration_plan(pending, now).remaining, pending)

    def test_round_zero_can_represent_bonus_round_without_turn_zero(self):
        for boundary in (Boundary.ROUND_START, Boundary.ROUND_END):
            now = TimePoint(boundary, 0)
            pending = (effect(deadlines=(TimePoint(boundary, 1),)),)
            self.assertEqual(expiration_plan(pending, now).remaining, pending)
        for boundary in (Boundary.TURN_START, Boundary.TURN_END):
            with self.assertRaises(ValueError):
                TimePoint(boundary, 0, 0)

    def test_same_kind_can_have_separate_instances_and_expiry(self):
        a = effect('first')
        b = effect('second', deadlines=(TimePoint(Boundary.TURN_START, 4, 1),))
        plan = expiration_plan((a, b), TimePoint(Boundary.TURN_START, 3, 1))
        self.assertEqual((plan.expired, plan.remaining), ((a,), (b,)))

    def test_planning_preserves_order_and_inputs_are_immutable(self):
        pending = (effect('a'), effect('b', deadlines=()), effect('c'))
        result = expiration_plan(pending, TimePoint(Boundary.TURN_START, 3, 1))
        self.assertEqual(tuple(item.token for item in result.expired), ('a', 'c'))
        self.assertEqual(tuple(item.token for item in pending), ('a', 'b', 'c'))
        with self.assertRaises(FrozenInstanceError):
            pending[0].subject = 1

    def test_invalid_clocks_are_rejected(self):
        cases = (('turn_start', 1, 0), (Boundary.TURN_START, 0, 0),
                 (Boundary.TURN_START, True, 0), (Boundary.TURN_START, 1.0, 0),
                 (Boundary.TURN_START, 1, None), (Boundary.TURN_START, 1, -1),
                 (Boundary.TURN_START, 1, False), (Boundary.ROUND_END, 1, 0))
        for args in cases:
            with self.assertRaises(ValueError):
                TimePoint(*args)

    def test_invalid_effect_definitions_are_rejected(self):
        original = effect()
        cases = ({'token': ''}, {'kind': None}, {'subject': False}, {'source': -1},
                 {'deadlines': []}, {'deadlines': (None,)},
                 {'deadlines': original.deadlines * 2}, {'rules': []}, {'rules': ('',)})
        for fields in cases:
            with self.assertRaises(ValueError):
                replace(original, **fields)

    def test_whole_plan_refuses_duplicate_tokens_and_mutable_input(self):
        now = TimePoint(Boundary.TURN_START, 3, 1)
        for pending in ((effect(), effect(subject=1)), [effect()], (effect(), None)):
            with self.assertRaises(ValueError):
                expiration_plan(pending, now)
        with self.assertRaises(ValueError):
            expiration_plan((effect(),), None)

    def test_bridge_expires_dodge_before_stun_and_before_action(self):
        game = battle(ModularDuel)
        game.fighters[0].dodging = True
        game.fighters[0].stunned_by = 0
        game.fighters[0].stun_expires_on_actor_turn = 1
        game._turn(0)
        event_types = [row['type'] for row in game.log]
        self.assertEqual(event_types[:3], ['dodge_end', 'condition_end', 'turn_start'])
        self.assertGreater(event_types.index('wait'), event_types.index('turn_start'))
        self.assertIsNone(game.fighters[0].stunned_by)
        self.assertFalse(game.fighters[0].dodging)

    def test_stun_without_deadline_remains_and_blocks_action(self):
        game = battle(ModularDuel)
        game.fighters[0].stunned_by = 1
        game._turn(0)
        self.assertEqual(game.fighters[0].stunned_by, 1)
        self.assertTrue(any(row['type'] == 'turn_skipped' for row in game.log))

    def test_timing_supports_many_actors_without_character_names(self):
        pending = tuple(effect(f'instance:{actor}', subject=actor, source=actor,
                               deadlines=(TimePoint(Boundary.TURN_START, 2, actor),))
                        for actor in (0, 1, 4, 7))
        result = expiration_plan(pending, TimePoint(Boundary.TURN_START, 2, 7))
        self.assertEqual(tuple(item.subject for item in result.expired), (7,))
        self.assertEqual(tuple(item.subject for item in result.remaining), (0, 1, 4))

    def test_expiration_grid_matches_reference_and_source_oracle(self):
        for actor, dodge0, dodge1, source, deadline, starts in product(
                (0, 1), (False, True), (False, True), (0, 1), (None, 1, 2, 3), (0, 1, 2)):
            old, new = battle(Duel), battle(ModularDuel)
            for game in (old, new):
                game.turn_counts[:] = [starts, starts]
                game.fighters[0].dodging, game.fighters[1].dodging = dodge0, dodge1
                game.fighters[1].stunned_by = source
                game.fighters[1].stun_expires_on_actor_turn = deadline
                game._turn(actor)
            should_end = source == actor and deadline is not None and starts + 1 >= deadline
            self.assertEqual(new.fighters[1].stunned_by, None if should_end else source)
            self.assertFalse(new.fighters[actor].dodging)
            self.assertEqual(new.fighters[1 - actor].dodging, (dodge0, dodge1)[1 - actor])
            self.assertEqual([vars(f) for f in old.fighters], [vars(f) for f in new.fighters])
            self.assertEqual(old.log, new.log)

    def test_frozen_pre_migration_replays_match_every_event_and_metric(self):
        root = Path(__file__).resolve().parents[1]
        cases = [root / 'results' / name for name in (
            'generic_sheet_dodge_demo.json', 'generic_sheet_modular_heal_demo.json',
            'generic_sheet_rank4_demo.json', 'generic_sheet_stance_demo.json',
            'generic_sheet_standard_shield_demo.json')]
        for path in cases:
            self.assertEqual(verify_result(path)[1], [], path.name)
            stored = json.loads(path.read_text(encoding='utf-8'))
            profiles = tuple(compile_duel(parse_sheet(data)) for data in stored['sheets'])
            policies = tuple(RulePolicy(**data) for data in stored['policies'])
            game = ModularDuel(profiles, policies, seed=stored['seed'],
                               initial_distance=stored['initial_distance'],
                               max_rounds=stored['max_rounds'], audit=True)
            # JSON normalization is only to compare serialized tuples and lists.
            replay = json.loads(json.dumps(asdict(game.run())))
            self.assertEqual(replay, stored['result'], path.name)


if __name__ == '__main__':
    unittest.main()
