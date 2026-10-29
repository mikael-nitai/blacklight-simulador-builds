from dataclasses import asdict, replace
from copy import deepcopy
import unittest

from blacklight.audit import audit_profiled_log
from blacklight.engine import IllegalAction, Move, Profile
from blacklight.result_audit import audit_battle_result
from blacklight.spatial_audit import audit_open_field_distance
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.runner import _require_engine_ruleset
from combatants.split_fast import SplitFastDuel, SplitFastPolicy
from experimental.prone_duel import ProneDuel, PronePolicy
from experimental.prone_duel_audit import audit_prone_log
from scripts.current_study_dev import INPUTS, configurations


def profile(name, *, agility=0, **kwargs):
    return Profile(name, 3, 100, 60, 4, agility, 5, 2, 14, 10 + agility,
                   5 + max(0, agility // 5), **kwargs)


class ProneDuelTests(unittest.TestCase):
    def setUp(self):
        self.profiles = (profile('A'), profile('B'))
        self.policies = (PronePolicy('A', knockback_stance=False),
                         PronePolicy('B', knockback_stance=False))

    def battle(self, *, initial=(False, False), seed=5, distance=1, profiles=None, policies=None):
        return ProneDuel(profiles or self.profiles, policies or self.policies, initial_prone=initial,
                         seed=seed, initial_distance=distance, max_rounds=5, audit=True,
                         action_registry=DEFAULT_ACTIONS)

    def test_close_and_ranged_modifiers_use_separate_sources(self):
        duel = self.battle(initial=(True, True))
        spec = duel._attack_check_spec(0, 'melee')
        self.assertEqual((spec.edges, spec.troubles), (1, 1))
        gunner = profile('A', agility=5, ranged_range=10)
        duel = self.battle(initial=(True, True), profiles=(gunner, self.profiles[1]))
        spec = duel._attack_check_spec(0, 'ranged')
        self.assertEqual((spec.edges, spec.troubles), (0, 1))

    def test_fast_strikes_edges_and_prone_trouble_remain_separate(self):
        attacker = profile('A', powers=frozenset({'fast_strikes', 'blazing_fast_fists'}),
                           traits=frozenset({'signature_fast_strikes'}))
        duel = self.battle(initial=(True, True), profiles=(attacker, self.profiles[1]))
        spec = duel._attack_check_spec(0, 'fast_strikes')
        self.assertEqual((spec.edges, spec.troubles), (3, 1))

    def test_prone_stunned_dodge_and_blazing_fists_modifiers_remain_distinct(self):
        attacker = profile('A', powers=frozenset({'blazing_fast_fists'}))
        duel = self.battle(initial=(True, True), profiles=(attacker, self.profiles[1]))
        duel.fighters[1].stunned_by = 0
        duel.fighters[1].dodging = True
        spec = duel._attack_check_spec(0, 'melee')
        self.assertEqual((spec.edges, spec.troubles), (2, 2))
        duel.stack_stunned_edge = True
        spec = duel._attack_check_spec(0, 'melee')
        self.assertEqual((spec.edges, spec.troubles), (3, 2))

    def test_standing_spends_one_space_before_moving(self):
        duel = self.battle(initial=(True, False), distance=10)
        duel.active_actor = 0
        duel.turn_counts[0] = 1
        duel.fighters[0].movement_available = True
        decision = duel.policies[0].choose_move(duel.observe(0))
        self.assertEqual(decision, Move('approach', 4))
        duel._move(0, decision)
        self.assertFalse(duel.prone[0])
        self.assertEqual(duel.distance, 6)
        self.assertEqual([e['type'] for e in duel.log][-2:], ['prone_stand', 'movement'])
        self.assertEqual(duel.log[-2]['cost'], 1)

    def test_stand_can_use_standard_movement_and_condition_does_not_expire(self):
        duel = self.battle(initial=(True, False), distance=10)
        duel.active_actor = 0
        duel.turn_counts[0] = 1
        duel.fighters[0].standard_available = True
        duel._start_turn_effects(0)
        self.assertTrue(duel.observe(0).me_prone)
        duel._move(0, Move('approach', 4), as_standard=True)
        self.assertFalse(duel.prone[0])
        self.assertFalse(duel.fighters[0].standard_available)
        self.assertTrue(duel.log[-2]['as_standard'])

    def test_bad_movement_or_declined_stand_does_not_mutate_state(self):
        for policy, move in ((self.policies[0], Move('approach', 5)),
                             (PronePolicy('A', stand_when_prone=False), Move('approach', 1))):
            duel = self.battle(initial=(True, False), distance=10,
                               policies=(policy, self.policies[1]))
            duel.active_actor = 0
            duel.turn_counts[0] = 1
            duel.fighters[0].movement_available = True
            before = (duel.distance, tuple(duel.prone), tuple(duel.log))
            with self.assertRaises(IllegalAction):
                duel._move(0, move)
            self.assertEqual((duel.distance, tuple(duel.prone), tuple(duel.log)), before)
            self.assertTrue(duel.fighters[0].movement_available)

    def test_declined_stand_preserves_condition_and_prone_attack(self):
        policy = PronePolicy('A', stand_when_prone=False, knockback_stance=False)
        duel = self.battle(initial=(True, False), policies=(policy, self.policies[1]))
        duel.active_actor = 0
        duel.turn_counts[0] = 1
        duel.fighters[0].movement_available = True
        duel._move(0, Move())
        self.assertTrue(duel.prone[0])
        self.assertEqual(duel._attack_check_spec(0, 'melee').troubles, 1)

    def test_no_speed_does_not_spend_imaginary_movement_to_stand(self):
        immobile = replace(self.profiles[0], run_speed=0, run_speed_exception=True)
        duel = self.battle(initial=(True, False), profiles=(immobile, self.profiles[1]))
        duel.active_actor = 0
        duel.turn_counts[0] = 1
        duel.fighters[0].movement_available = True
        duel._move(0, Move())
        self.assertTrue(duel.prone[0])
        self.assertFalse(any(event['type'] == 'prone_stand' for event in duel.log))

    def test_without_prone_old_replays_are_unchanged(self):
        baseline_policies = tuple(SplitFastPolicy(p.name, knockback_stance=False) for p in self.policies)
        for seed in range(20):
            baseline = SplitFastDuel(self.profiles, baseline_policies, seed=seed, initial_distance=3,
                                     max_rounds=5, audit=True, action_registry=DEFAULT_ACTIONS).run()
            duel = self.battle(seed=seed, distance=3)
            result = duel.run()
            self.assertEqual(result, baseline)

    def test_full_experimental_trace_passes_existing_audits(self):
        duel = self.battle(initial=(True, True), distance=3)
        result = duel.run()
        self.assertEqual(audit_profiled_log(result.log, self.profiles, ruleset=duel.table_ruleset), [])
        self.assertEqual(audit_open_field_distance(result.log, 3), [])
        self.assertEqual(audit_prone_log(result.log, self.profiles, initial_prone=(True, True),
                                         initial_distance=3), [])

    def test_full_prone_and_fast_traces_pass_independent_audits(self):
        attacker = profile('A', powers=frozenset({'fast_strikes', 'blazing_fast_fists'}),
                           traits=frozenset({'signature_fast_strikes'}))
        profiles = (attacker, self.profiles[1])
        policies = (PronePolicy('A', prefer_fast=True, stand_when_prone=False, knockback_stance=False),
                    PronePolicy('B', stand_when_prone=False, knockback_stance=False))
        for initial in ((False, False), (False, True), (True, False), (True, True)):
            for seed in range(10):
                with self.subTest(initial=initial, seed=seed):
                    duel = self.battle(initial=initial, seed=seed, profiles=profiles, policies=policies)
                    result = duel.run()
                    self.assertEqual(audit_profiled_log(result.log, profiles, ruleset=duel.table_ruleset), [])
                    self.assertEqual(audit_battle_result(result, profiles, expected_seed=seed, max_rounds=5), [])
                    self.assertEqual(audit_open_field_distance(result.log, 1), [])
                    self.assertEqual(audit_prone_log(result.log, profiles, initial_prone=initial,
                                                     initial_distance=1), [])

    def test_independent_audit_rejects_forged_condition_and_modifiers(self):
        policies = (PronePolicy('A', stand_when_prone=False), PronePolicy('B', stand_when_prone=False))
        duel = self.battle(initial=(True, True), policies=policies)
        log = list(duel.run().log)
        check = next(i for i, event in enumerate(log) if event['type'] == 'prone_check')
        for key, value in (('added_edges', 99), ('attacker_prone', False), ('trigger', 999)):
            forged = deepcopy(log)
            forged[check][key] = value
            with self.subTest(key=key):
                self.assertTrue(audit_prone_log(forged, self.profiles, initial_prone=(True, True),
                                                initial_distance=1))
        missing = deepcopy(log)
        missing.pop(check)
        self.assertTrue(audit_prone_log(missing, self.profiles, initial_prone=(True, True),
                                        initial_distance=1))
        forged = deepcopy(log)
        attack = next(event for event in forged if event['type'] == 'attack')
        attack['edges'] += 1
        self.assertTrue(audit_prone_log(forged, self.profiles, initial_prone=(True, True),
                                        initial_distance=1))
        for key in ('trigger', 'actor', 'target'):
            forged = deepcopy(log)
            attack = next(event for event in forged if event['type'] == 'attack')
            attack[key] = []
            with self.subTest(malformed=key):
                self.assertTrue(audit_prone_log(forged, self.profiles, initial_prone=(True, True),
                                                initial_distance=1))

    def test_independent_audit_rejects_forged_stand_cost_and_speed(self):
        duel = self.battle(initial=(True, False), distance=8)
        log = list(duel.run().log)
        stand = next(i for i, event in enumerate(log) if event['type'] == 'prone_stand')
        for key, value in (('cost', True), ('cost', 0), ('speed', 99), ('as_standard', 'yes')):
            forged = deepcopy(log)
            forged[stand][key] = value
            with self.subTest(key=key, value=value):
                self.assertTrue(audit_prone_log(forged, self.profiles, initial_prone=(True, False),
                                                initial_distance=8))
        forged = deepcopy(log)
        forged[stand + 1]['steps'] = self.profiles[0].run_speed
        self.assertTrue(audit_prone_log(forged, self.profiles, initial_prone=(True, False),
                                        initial_distance=8))

    def test_scope_and_unknown_mechanics_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'experimental engine'):
            _require_engine_ruleset(ProneDuel, ProneDuel.table_ruleset, None)
        unknown = replace(self.profiles[0], powers=frozenset({'unknown'}))
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            self.battle(profiles=(unknown, self.profiles[1]))
        with self.assertRaisesRegex(ValueError, 'stand'):
            self.battle(policies=(SplitFastPolicy('A'), self.policies[1]))

    def test_victor_mirror_interactions_in_audited_full_traces(self):
        hero, choices, scenarios = configurations(tuple(path.read_bytes() for path in INPUTS))
        foe, foe_policy, distance, _ = scenarios['mirror']
        profiles = (compile_duel(hero), compile_duel(foe))
        policies = (PronePolicy(**asdict(choices['hammer_fast_hammer']), stand_when_prone=False),
                    PronePolicy(**asdict(foe_policy), stand_when_prone=False))
        observed = set()
        for initial in ((True, False), (False, True), (True, True)):
            for seed in range(20):
                with self.subTest(initial=initial, seed=seed):
                    duel = self.battle(initial=initial, seed=seed, distance=distance,
                                       profiles=profiles, policies=policies)
                    result = duel.run()
                    observed.update(event['type'] for event in result.log)
                    if any(event.get('type') == 'condition_start' and event.get('condition') == 'stunned'
                           for event in result.log):
                        observed.add('stunned')
                    if any(event.get('type') == 'attack' and event.get('reaction') is True
                           for event in result.log):
                        observed.add('riposte')
                    self.assertEqual(audit_profiled_log(result.log, profiles, ruleset=duel.table_ruleset), [])
                    self.assertEqual(audit_battle_result(result, profiles, expected_seed=seed, max_rounds=5), [])
                    self.assertEqual(audit_open_field_distance(result.log, distance), [])
                    self.assertEqual(audit_prone_log(result.log, profiles, initial_prone=initial,
                                                     initial_distance=distance), [])
        self.assertTrue({'shield_activate', 'stunned', 'riposte'} <= observed)

    def test_explicit_stunned_edge_variant_is_audited_separately(self):
        hero, choices, scenarios = configurations(tuple(path.read_bytes() for path in INPUTS))
        foe, foe_policy, distance, _ = scenarios['mirror']
        profiles = (compile_duel(hero), compile_duel(foe))
        policies = (PronePolicy(**asdict(choices['hammer_fast_hammer']), stand_when_prone=False),
                    PronePolicy(**asdict(foe_policy), stand_when_prone=False))
        for seed in range(10):
            duel = self.battle(initial=(True, True), seed=seed, distance=distance,
                               profiles=profiles, policies=policies)
            duel.stack_stunned_edge = True
            result = duel.run()
            self.assertEqual(audit_prone_log(result.log, profiles, initial_prone=(True, True),
                                             initial_distance=distance, stack_stunned_edge=True), [])
