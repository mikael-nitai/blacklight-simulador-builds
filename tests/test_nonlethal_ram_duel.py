from copy import deepcopy
from dataclasses import asdict, replace
import unittest

from blacklight.engine import IllegalAction, Move, Profile
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.runner import _require_engine_ruleset
from experimental.nonlethal_ram_audit import audit_nonlethal_ram_duel
from experimental.nonlethal_ram_duel import NonlethalRamProneDuel
from experimental.ram_prone_duel import RamProneDuel, RamPronePolicy
from scripts.current_study_holdout import INPUTS, holdout_configurations


class StationaryPolicy(RamPronePolicy):
    def choose_move(self, observation):
        return Move()


def profile(name, melee, *, health=100, initiative=0, **kwargs):
    return Profile(name, 3, health, 60, melee, 0, 5, 2, 10 + melee, 10, 5,
                   initiative_modifier=initiative, **kwargs)


class NonlethalRamDuelTests(unittest.TestCase):
    def setUp(self):
        self.profiles = (profile('A', 4, initiative=100), profile('B', 2, health=1))
        self.policies = (RamPronePolicy('A', use_ram=False),
                         StationaryPolicy('B', always_wait=True, use_ram=False))

    def run_duel(self, cls=NonlethalRamProneDuel, *, seed=1, profiles=None, distance=1):
        return cls(profiles or self.profiles, self.policies, seed=seed, initial_distance=distance,
                   initial_prone=(False, False), max_rounds=1, audit=True,
                   action_registry=DEFAULT_ACTIONS).run()

    def audit(self, result, profiles=None, *, distance=1, seed=1):
        return audit_nonlethal_ram_duel(result, profiles or self.profiles,
                                        initial_prone=(False, False), initial_distance=distance,
                                        expected_seed=seed, max_rounds=1, ruleset='split_fast_v3')

    def test_default_unarmed_nonhero_stops_one_point_before_death(self):
        historic = self.run_duel(RamProneDuel)
        corrected = self.run_duel()
        self.assertEqual(historic.final_health[1], -19)
        self.assertEqual(corrected.final_health[1], 0)
        event = next(event for event in corrected.log if event['type'] == 'attack' and event['actor'] == 'A')
        self.assertEqual((event['nonlethal_floor'], event['nonlethal_raw_after'], event['nonlethal_prevented']),
                         (0, -19, 19))
        self.assertEqual((event['damage'], corrected.metrics[0]['damage_dealt'],
                          corrected.metrics[1]['damage_taken']), (1, 1, 1))
        self.assertEqual(self.audit(corrected), [])
        self.assertTrue(self.audit(historic))

    def test_when_floor_is_not_reached_existing_replays_match(self):
        profiles = (self.profiles[0], replace(self.profiles[1], max_health=1000))
        for seed in range(20):
            prior = self.run_duel(RamProneDuel, seed=seed, profiles=profiles)
            current = self.run_duel(seed=seed, profiles=profiles)
            self.assertEqual(prior, current)
            self.assertEqual(self.audit(current, profiles, seed=seed), [])

    def test_armed_nonhero_bare_attack_fails_closed(self):
        armed = replace(self.profiles[0], weapons=frozenset({'hammer'}))
        with self.assertRaisesRegex(IllegalAction, 'armed profile'):
            self.run_duel(profiles=(armed, self.profiles[1]))

    def test_weaponless_fast_strikes_cap_each_successful_limb(self):
        attacker = replace(self.profiles[0], powers=frozenset({'fast_strikes'}))
        profiles = (attacker, self.profiles[1])
        policies = (RamPronePolicy('A', prefer_fast=True, use_ram=False), self.policies[1])
        seen = False
        for seed in range(20):
            duel = NonlethalRamProneDuel(profiles, policies, seed=seed, initial_distance=1,
                                         initial_prone=(False, False), max_rounds=1, audit=True,
                                         action_registry=DEFAULT_ACTIONS)
            result = duel.run()
            self.assertEqual(self.audit(result, profiles, seed=seed), [])
            arms = [event for event in result.log if event['type'] == 'attack' and event['actor'] == 'A']
            if any('nonlethal_floor' in event for event in arms):
                seen = True
                self.assertGreaterEqual(result.final_health[1], 0)
                self.assertTrue(all(event['health_after'] >= 0 for event in arms))
        self.assertTrue(seen)

    def test_nonlethal_marker_forgery_is_detected(self):
        result = self.run_duel()
        index = next(i for i, event in enumerate(result.log) if event['type'] == 'attack' and event['actor'] == 'A')
        for key, value in (('nonlethal_floor', 2), ('nonlethal_prevented', True),
                           ('health_after', -19), ('damage', 20)):
            with self.subTest(key=key):
                log = deepcopy(list(result.log))
                log[index][key] = value
                self.assertTrue(self.audit(replace(result, log=tuple(log))))

    def test_experimental_host_is_not_the_certified_runner(self):
        with self.assertRaisesRegex(RuntimeError, 'experimental engine'):
            _require_engine_ruleset(NonlethalRamProneDuel, NonlethalRamProneDuel.table_ruleset, None)

    def test_current_victor_ram_replay_matches_when_correction_not_needed(self):
        hero, choices, scenarios = holdout_configurations(tuple(path.read_bytes() for path in INPUTS))
        foe, foe_policy, distance, _ = scenarios['gunner_open']
        profiles = (compile_duel(hero), compile_duel(foe))
        policies = (RamPronePolicy(**asdict(choices['hammer_fast_hammer'])),
                    RamPronePolicy(**asdict(foe_policy), use_ram=False))
        arguments = dict(initial_prone=(False, False), seed=987654, initial_distance=distance,
                         max_rounds=30, audit=True, action_registry=DEFAULT_ACTIONS)
        baseline = RamProneDuel(profiles, policies, **arguments).run()
        corrected = NonlethalRamProneDuel(profiles, policies, **arguments).run()
        self.assertEqual(corrected, baseline)
        self.assertEqual(audit_nonlethal_ram_duel(corrected, profiles, initial_prone=(False, False),
                                                  initial_distance=distance, expected_seed=987654,
                                                  max_rounds=30, ruleset='split_fast_v3'), [])
