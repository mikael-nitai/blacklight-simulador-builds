"""Source-based oracles for the bridge shared by current combat prototypes."""

from dataclasses import FrozenInstanceError, asdict, replace
from itertools import product
import json
from pathlib import Path
import unittest

from blacklight.engine import Fighter, Profile, blacklight_profile
from blacklight.policies import ATTACK, RulePolicy
from combatants.condition_bridge import ConditionTiming, expire_at_turn_start, turn_start_plan
from experimental.corridor import CorridorDuel
from experimental.focus_duel import FocusDuel
from experimental.group import GroupBattle
from experimental.group_policies import GroupPolicy
from scripts.verify_sources import verify_result


ROOT = Path(__file__).resolve().parents[1]


def profile(index):
    return Profile(f'P{index}', 3, 90, 60, 4, 2, 3, 2, 14, 12, 5)


def restored_profile(data):
    return Profile(**{key: frozenset(value) if key in ('powers', 'traits', 'weapons') else value
                       for key, value in data.items()})


class TestSharedConditions(unittest.TestCase):
    def test_planning_supports_roster_size_and_subject_scope(self):
        states = tuple(ConditionTiming(True, 3, 2) for _ in range(8))
        plan = turn_start_plan(states, (1, 1, 1, 2, 1, 1, 1, 1), 3,
                                stun_subjects=(0, 4, 7))
        self.assertEqual(tuple((effect.kind, effect.subject) for effect in plan.expired),
                         (('dodge', 3), ('stunned', 0), ('stunned', 4), ('stunned', 7)))
        with self.assertRaises(FrozenInstanceError):
            states[0].dodging = False

    def test_focus_scope_does_not_invent_dodge_or_self_stun_handling(self):
        states = (ConditionTiming(True, 0, 1), ConditionTiming(True, 0, 1))
        plan = turn_start_plan(states, (1, 0), 0,
                                include_dodge=False, stun_subjects=(1,))
        self.assertEqual(tuple((effect.kind, effect.subject) for effect in plan.expired),
                         (('stunned', 1),))

    def test_no_deadline_remains_pending_and_unstunned_orphan_is_ignored(self):
        states = (ConditionTiming(False, None, 1), ConditionTiming(False, 0, None))
        plan = turn_start_plan(states, (5, 4), 0)
        self.assertEqual(plan.expired, ())
        self.assertEqual(tuple(item.subject for item in plan.remaining), (1,))

    def test_invalid_roster_and_clock_are_rejected(self):
        states = (ConditionTiming(False, None, None),) * 2
        cases = (([], (1, 0), 0), ((), (), 0),
                 (states, [1, 0], 0), (states, (1,), 0),
                 (states, (True, 0), 0), (states, (1.0, 0), 0),
                 (states, (0, 0), 0), (states, (1, -1), 0),
                 (states, (1, 0), False), (states, (1, 0), 2),
                 ((None, states[0]), (1, 0), 0),
                 ((ConditionTiming(False, 2, 1), states[0]), (1, 0), 0))
        for roster, counts, actor in cases:
            with self.assertRaises(ValueError):
                turn_start_plan(roster, counts, actor)

    def test_invalid_snapshots_and_options_are_rejected(self):
        for args in ((0, None, None), (False, True, 1), (False, -1, 1),
                     (False, 0, 0), (False, 0, False), (False, 0, 1.0)):
            with self.assertRaises(ValueError):
                ConditionTiming(*args)
        states = (ConditionTiming(False, None, None),) * 2
        for subjects in ((0, 0), (True,), (2,), [-1]):
            with self.assertRaises(ValueError):
                turn_start_plan(states, (1, 0), 0, stun_subjects=subjects)
        with self.assertRaises(ValueError):
            turn_start_plan(states, (1, 0), 0, include_dodge=1)

    def test_invalid_later_subject_cannot_partially_expire_earlier_flags(self):
        fighters = [Fighter(profile(index)) for index in range(3)]
        fighters[0].dodging = True
        fighters[0].stunned_by = 0
        fighters[0].stun_expires_on_actor_turn = 1
        fighters[2].stunned_by = 5
        before = [vars(item).copy() for item in fighters]
        log = []
        with self.assertRaises(ValueError):
            expire_at_turn_start(fighters, [1, 0, 0], 0, lambda *args, **data: log.append(data))
        self.assertEqual([vars(item) for item in fighters], before)
        self.assertEqual(log, [])

    def test_invalid_recorder_cannot_clear_flags(self):
        fighter = Fighter(profile(0))
        fighter.dodging = True
        with self.assertRaises(ValueError):
            expire_at_turn_start((fighter,), (1,), 0, None)
        self.assertTrue(fighter.dodging)

    def test_invalid_later_name_cannot_clear_earlier_flags(self):
        for name in ('', None, 'P0'):
            fighters = [Fighter(profile(0)), Fighter(replace(profile(1), name=name))]
            fighters[0].dodging = True
            log = []
            with self.assertRaises(ValueError):
                expire_at_turn_start(fighters, (1, 0), 0,
                                      lambda *args, **data: log.append(data))
            self.assertTrue(fighters[0].dodging)
            self.assertEqual(log, [])

    def test_direct_flag_and_log_oracle_for_three_actors(self):
        for actor, source, deadline, count in product(range(3), range(3), (None, 1, 3), (1, 2, 3)):
            fighters = [Fighter(profile(index)) for index in range(3)]
            for fighter in fighters:
                fighter.dodging = True
                fighter.stunned_by = source
                fighter.stun_expires_on_actor_turn = deadline
            counts = [0, 0, 0]
            counts[actor] = count
            log = []
            def record(kind, rules, **data):
                log.append((kind, tuple(rules), data))
            expire_at_turn_start(fighters, counts, actor, record)
            due = source == actor and deadline is not None and count >= deadline
            self.assertEqual([f.stunned_by for f in fighters], [None if due else source] * 3)
            self.assertEqual([f.dodging for f in fighters], [i != actor for i in range(3)])
            expected = [('dodge_end', ('ACT-07',), {'actor': f'P{actor}'})]
            if due:
                expected.extend(('condition_end', ('COND-02',),
                                 {'actor': f'P{i}', 'condition': 'stunned'}) for i in range(3))
            self.assertEqual(log, expected)

    def test_group_self_stun_expires_before_action_but_ko_clock_does_not_advance(self):
        profiles = tuple(profile(i) for i in range(3))
        policies = (GroupPolicy('attack', preferred='melee'),) * 3
        game = GroupBattle(profiles, policies, seed=1, audit=True)
        game.fighters[0].stunned_by = 0
        game.fighters[0].stun_expires_on_actor_turn = 1
        game._turn(0)
        self.assertEqual([row['type'] for row in game.log[:2]], ['condition_end', 'turn_start'])
        self.assertIsNone(game.fighters[0].stunned_by)
        before = (list(game.turn_counts), len(game.log))
        game.fighters[1].health = 0
        game._turn(1)
        self.assertEqual((game.turn_counts, len(game.log)), before)

    def test_focus_self_stun_and_shattered_guard_preserve_existing_scope(self):
        hero = blacklight_profile()
        foe = replace(profile(1), powers=frozenset({'mental_punch'}))
        game = FocusDuel(hero, foe, strategy='hammer', shield_focus_reduction=0,
                          seed=1, audit=True)
        game.fighters[0].stunned_by = 0
        game.fighters[0].stun_expires_on_actor_turn = 1
        game._turn(0)
        self.assertEqual(game.fighters[0].stunned_by, 0)
        self.assertEqual([row['type'] for row in game.log[:2]], ['turn_start', 'turn_skipped'])
        game.fighters[1].focus = -game.fighters[1].profile.max_focus
        before = (list(game.turn_counts), len(game.log))
        game._turn(1)
        self.assertEqual((game.turn_counts, len(game.log)), before)

    def test_frozen_extension_replays_keep_all_events_and_map_state(self):
        names = ('group_pool_v2_demo_G2_shield_0.json',
                 'focus_pool_v2_demo_M4_F0_shield_0.json',
                 'corridor_pool_v2_demo_L20_C2_fast_0.json')
        for name in names:
            path = ROOT / 'results' / name
            self.assertEqual(verify_result(path)[1], [], name)
            data = json.loads(path.read_text(encoding='utf-8'))
            profiles = tuple(restored_profile(row) for row in data['profiles'])
            if name.startswith('group'):
                game = GroupBattle(profiles, tuple(GroupPolicy(**row) for row in data['policies']),
                                    seed=data['seed'], audit=True)
            elif name.startswith('focus'):
                game = FocusDuel(*profiles, strategy=data['strategy'], shield_focus_reduction=0,
                                  seed=data['seed'], audit=True)
            else:
                game = CorridorDuel(profiles, tuple(RulePolicy(**row) for row in data['policies']),
                                     seed=data['seed'], length=data['length'],
                                     initial_positions=tuple(data['initial_positions']), audit=True)
            result = json.loads(json.dumps(asdict(game.run())))
            self.assertEqual(result, data['result'], name)
            if name.startswith('corridor'):
                self.assertEqual(game.positions, data['final_positions'])
                self.assertEqual(game.wall_reached, data['wall_reached'])
                self.assertEqual(game.contact_occurred, data['contact_occurred'])

    def test_extension_manifests_cover_shared_mechanics(self):
        from hashlib import sha256
        from scripts import corridor_experiment, focus_experiment, group_experiment
        for module in (corridor_experiment, focus_experiment, group_experiment):
            sources = module.hashes()
            for source in ('combatants/condition_bridge.py', 'combatants/lifecycle.py',
                           'combatants/modular_duel.py', 'combatants/actions.py'):
                self.assertEqual(sources[source], sha256((ROOT / source).read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
