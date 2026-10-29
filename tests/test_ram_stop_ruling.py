from copy import deepcopy
from dataclasses import replace
import unittest

from blacklight.engine import IllegalAction
from combatants.actions import DEFAULT_ACTIONS
from experimental.nonlethal_ram_audit import audit_nonlethal_ram_duel
from experimental.ram_incapacity_duel import RamIncapacityDuel
from experimental.ram_prone_duel import RamPronePolicy
from tests.test_ram_incapacity_duel import StationaryPolicy, profile

MODE = 'stop_before_heal_reject_lethal'


class RamStopRulingTests(unittest.TestCase):
    def setUp(self):
        self.profiles = (profile('A', 4, health=20, initiative=100, powers=frozenset({'healing_factor'})),
                         profile('B', 2, health=250))
        self.policies = (RamPronePolicy('A'), StationaryPolicy('B', always_wait=True, use_ram=False))

    def run_duel(self, profiles=None, seed=1):
        profiles = profiles or self.profiles
        duel = RamIncapacityDuel(profiles, self.policies, self_damage_mode=MODE, stop_on_attacker='A',
                                 initial_prone=(False, False), seed=seed, initial_distance=10,
                                 max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
        return duel, duel.run()

    def audit(self, duel, result, profiles=None):
        return audit_nonlethal_ram_duel(result, profiles or self.profiles,
                initial_prone=(False, False), initial_distance=10, expected_seed=duel.seed,
                max_rounds=1, ruleset=duel.table_ruleset, self_damage_mode=MODE, stop_on_attacker='A')

    def test_both_take_damage_and_combat_ends_before_healing(self):
        duel, result = self.run_duel()
        attack = next(e for e in result.log if e['type'] == 'ram_attack')
        stop = next(e for e in result.log if e['type'] == 'ram_incapacity_stop')
        self.assertEqual((result.final_health, result.outcome, result.winner), ((-1, 210), 'win', 'B'))
        self.assertGreater(attack['attacker_damage_applied'], 0)
        self.assertGreater(attack['target_damage_applied'], 0)
        self.assertEqual(stop['trigger'], attack['trigger'])
        self.assertEqual(result.log[-1]['type'], 'turn_end')
        self.assertFalse(any(e['type'] == 'heal' and e['actor'] == 'A' for e in result.log))
        self.assertEqual(self.audit(duel, result), [])
        self.assertEqual(result, self.run_duel()[1])

    def test_both_unconscious_are_draw_before_recovery(self):
        profiles = (self.profiles[0], replace(self.profiles[1], max_health=1))
        duel, result = self.run_duel(profiles)
        self.assertEqual((result.final_health, result.outcome, result.winner), ((-1, 0), 'draw', None))
        self.assertEqual(self.audit(duel, result, profiles), [])

    def test_death_threshold_aborts_instead_of_assuming_a_ruling(self):
        profiles = (replace(self.profiles[0], max_health=1), self.profiles[1])
        duel = RamIncapacityDuel(profiles, self.policies, self_damage_mode=MODE, stop_on_attacker='A',
                                 initial_prone=(False, False), seed=1, initial_distance=10,
                                 max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
        with self.assertRaisesRegex(IllegalAction, 'death threshold is undecided'):
            duel.run()
        self.assertFalse(any(e['type'] == 'ram_attack' for e in duel.log))

    def test_ruling_requires_a_named_attacker_and_does_not_cover_others(self):
        args = dict(initial_prone=(False, False), seed=1, initial_distance=10,
                    max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
        with self.assertRaises(ValueError):
            RamIncapacityDuel(self.profiles, self.policies, self_damage_mode=MODE, **args)
        duel = RamIncapacityDuel(self.profiles, self.policies, self_damage_mode=MODE,
                                 stop_on_attacker='B', **args)
        with self.assertRaisesRegex(IllegalAction, 'for this attacker is undecided'):
            duel.run()

    def test_no_incapacitation_keeps_normal_healing(self):
        profiles = (replace(self.profiles[0], max_health=200), self.profiles[1])
        duel, result = self.run_duel(profiles)
        self.assertFalse(any(e['type'] == 'ram_incapacity_stop' for e in result.log))
        self.assertTrue(any(e['type'] == 'heal' and e['actor'] == 'A' for e in result.log))
        self.assertEqual(self.audit(duel, result, profiles), [])

    def test_enemy_riposte_does_not_trigger_the_ram_self_damage_ruling(self):
        profiles = (profile('A', 0, health=15, initiative=100, powers=frozenset({'healing_factor'})),
                    profile('B', 4, health=250, powers=frozenset({'riposte'})))
        duel, result = self.run_duel(profiles, seed=0)
        ram = next(event for event in result.log if event['type'] == 'ram_attack')
        self.assertFalse(ram['transaction']['parameters']['success'])
        self.assertEqual(ram['attacker_health_after'], 15)
        self.assertTrue(any(event['type'] == 'attack' and event.get('reaction') is True
                            and event.get('health_after') == 0 for event in result.log))
        self.assertFalse(any(event['type'] == 'ram_incapacity_stop' for event in result.log))
        self.assertEqual(result.final_health[0], 5)
        self.assertEqual(self.audit(duel, result, profiles), [])

    def test_forged_stop_or_postimpact_healing_is_rejected(self):
        duel, result = self.run_duel()
        index = next(i for i, e in enumerate(result.log) if e['type'] == 'ram_incapacity_stop')
        for key, value in (('health', 0), ('trigger', 999), ('reason', 'incorrect')):
            log = deepcopy(result.log)
            log[index][key] = value
            self.assertTrue(self.audit(duel, replace(result, log=log)))
        log = list(deepcopy(result.log))
        log.pop(index)
        for seq, event in enumerate(log, 1):
            event['seq'] = seq
        self.assertTrue(self.audit(duel, replace(result, log=tuple(log))))
        log = list(deepcopy(result.log))
        stop = log[index]
        log.insert(index + 1, {'type': 'heal', 'actor': 'A', 'round': stop['round'],
                               'bonus_round': stop['bonus_round'], 'rules': ['POW-03'],
                               'proposed': 5, 'effective': 5, 'health_before': -1,
                               'health_after': 4})
        log[-1]['health'] = 4
        for seq, event in enumerate(log, 1):
            event['seq'] = seq
        metrics = tuple(dict(row) for row in result.metrics)
        metrics[0]['healing_effective'] += 5
        forged = replace(result, log=tuple(log), metrics=metrics, final_health=(4, 210),
                         outcome='inconclusive', winner=None)
        self.assertTrue(self.audit(duel, forged))
