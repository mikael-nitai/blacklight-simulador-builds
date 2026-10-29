from copy import deepcopy
from dataclasses import replace
import unittest

from blacklight.engine import Move, Profile
from combatants.actions import DEFAULT_ACTIONS
from combatants.runner import _require_engine_ruleset
from experimental.nonlethal_ram_audit import audit_nonlethal_ram_duel
from experimental.ram_incapacity_duel import RamIncapacityDuel
from experimental.ram_prone_duel import RamPronePolicy


class StationaryPolicy(RamPronePolicy):
    def choose_move(self, observation):
        return Move()


def profile(name, melee, *, health, initiative=0, powers=frozenset()):
    return Profile(name, 3, health, 60, melee, 0, 5, 2, 10 + melee, 10, 5,
                   initiative_modifier=initiative, powers=powers)


class RamIncapacityDuelTests(unittest.TestCase):
    def setUp(self):
        self.profiles = (profile('A', 4, health=1, initiative=100, powers=frozenset({'healing_factor'})),
                         profile('B', 2, health=250))
        self.policies = (RamPronePolicy('A'), StationaryPolicy('B', always_wait=True, use_ram=False))

    def run_mode(self, mode, *, seed=1, profiles=None):
        duel = RamIncapacityDuel(profiles or self.profiles, self.policies, self_damage_mode=mode,
                                 initial_prone=(False, False), seed=seed, initial_distance=10,
                                 max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
        return duel, duel.run()

    def audit(self, duel, result, profiles=None, mode=None):
        return audit_nonlethal_ram_duel(result, profiles or self.profiles,
                                        initial_prone=(False, False), initial_distance=10,
                                        expected_seed=duel.seed, max_rounds=1,
                                        ruleset=duel.table_ruleset,
                                        self_damage_mode=mode or duel.self_damage_mode)

    def test_lethal_impact_death_prevents_healing_but_target_still_takes_damage(self):
        duel, result = self.run_mode('lethal_impact')
        attack = next(event for event in result.log if event['type'] == 'ram_attack')
        self.assertLessEqual(attack['attacker_health_after'], -1)
        self.assertGreater(attack['target_damage_applied'], 0)
        self.assertEqual(result.winner, 'B')
        self.assertTrue(any(event['type'] == 'incapacity_dead' and event['actor'] == 'A' for event in result.log))
        after_ram = list(result.log)[list(result.log).index(attack) + 1:]
        self.assertFalse(any(event['type'] == 'heal' and event['actor'] == 'A' for event in after_ram))
        self.assertEqual(self.audit(duel, result), [])

    def test_nonlethal_impact_caps_self_damage_and_allows_end_turn_healing(self):
        duel, result = self.run_mode('nonlethal_impact')
        attack = next(event for event in result.log if event['type'] == 'ram_attack')
        self.assertLess(attack['transaction']['after']['attacker_health'], 0)
        self.assertEqual(attack['attacker_health_after'], 0)
        self.assertEqual(attack['attacker_damage_applied'], 1)
        self.assertGreater(attack['target_damage_applied'], 0)
        self.assertEqual(result.final_health[0], 1)
        self.assertEqual(result.outcome, 'inconclusive')
        self.assertTrue(any(event['type'] == 'heal' and event['actor'] == 'A' for event in result.log))
        self.assertEqual(self.audit(duel, result), [])

    def test_simultaneous_double_incapacity_changes_outcome_by_hypothesis(self):
        profiles = (self.profiles[0], replace(self.profiles[1], max_health=1))
        lethal_duel, lethal = self.run_mode('lethal_impact', profiles=profiles)
        nonlethal_duel, nonlethal = self.run_mode('nonlethal_impact', profiles=profiles)
        self.assertEqual((lethal.outcome, lethal.winner), ('draw', None))
        self.assertEqual((nonlethal.outcome, nonlethal.winner), ('win', 'A'))
        self.assertEqual(lethal.final_health[1], 0)
        self.assertEqual(nonlethal.final_health, (1, 0))
        self.assertEqual(self.audit(lethal_duel, lethal, profiles), [])
        self.assertEqual(self.audit(nonlethal_duel, nonlethal, profiles), [])

    def test_modes_are_explicit_and_not_interchangeable(self):
        with self.assertRaises(ValueError):
            self.run_mode('unknown')
        duel, result = self.run_mode('lethal_impact')
        self.assertTrue(self.audit(duel, result, mode='nonlethal_impact'))
        with self.assertRaisesRegex(RuntimeError, 'experimental engine'):
            _require_engine_ruleset(RamIncapacityDuel, RamIncapacityDuel.table_ruleset, None)

    def test_mode_is_recorded_even_when_no_ram_occurs(self):
        duel = RamIncapacityDuel(self.profiles, self.policies, self_damage_mode='lethal_impact',
                                 initial_prone=(False, False), seed=1, initial_distance=1,
                                 max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
        result = duel.run()
        self.assertFalse(any(event['type'] == 'ram_attack' for event in result.log))
        self.assertEqual(next(event['mode'] for event in result.log if event['type'] == 'incapacity_contract'),
                         'lethal_impact')
        context = dict(initial_prone=(False, False), initial_distance=1, expected_seed=1,
                       max_rounds=1, ruleset=duel.table_ruleset)
        self.assertEqual(audit_nonlethal_ram_duel(result, self.profiles,
                                                  self_damage_mode='lethal_impact', **context), [])
        self.assertTrue(audit_nonlethal_ram_duel(result, self.profiles,
                                                 self_damage_mode='nonlethal_impact', **context))

    def test_forged_self_damage_or_death_marker_is_rejected(self):
        duel, result = self.run_mode('lethal_impact')
        log = deepcopy(list(result.log))
        attack = next(event for event in log if event['type'] == 'ram_attack')
        attack['attacker_health_after'] = 0
        self.assertTrue(self.audit(duel, replace(result, log=tuple(log))))
        log = deepcopy(list(result.log))
        marker = next(event for event in log if event['type'] == 'incapacity_dead')
        marker['mode'] = 'nonlethal_impact'
        self.assertTrue(self.audit(duel, replace(result, log=tuple(log))))

    def test_audit_rejects_consistent_but_impossible_healing_after_death(self):
        duel, result = self.run_mode('lethal_impact')
        log = deepcopy(list(result.log))
        marker_index = next(i for i, event in enumerate(log) if event['type'] == 'incapacity_dead')
        marker = log[marker_index]
        old = marker['health']
        log.insert(marker_index, {'type': 'heal', 'actor': 'A', 'round': marker['round'],
                                  'bonus_round': marker['bonus_round'], 'rules': ['POW-03'],
                                  'proposed': 5, 'effective': 5, 'health_before': old,
                                  'health_after': old + 5})
        marker['health'] = old + 5
        next(event for event in log[marker_index + 1:] if event['type'] == 'turn_end' and event['actor'] == 'A')['health'] = old + 5
        for index, event in enumerate(log, 1):
            event['seq'] = index
        metrics = tuple(dict(row) for row in result.metrics)
        metrics[0]['healing_effective'] += 5
        forged = replace(result, log=tuple(log), metrics=metrics,
                         final_health=(old + 5, result.final_health[1]))
        self.assertTrue(any('dead actor received' in issue for issue in self.audit(duel, forged)))

    def test_same_seed_reproduces_entire_hypothesis(self):
        for mode in ('lethal_impact', 'nonlethal_impact'):
            self.assertEqual(self.run_mode(mode)[1], self.run_mode(mode)[1])

    def test_living_unconscious_attacker_recovers_at_end_of_turn_in_hypothesis(self):
        profiles = (replace(self.profiles[0], max_health=20), self.profiles[1])
        found = False
        for seed in range(150):
            duel, result = self.run_mode('lethal_impact', seed=seed, profiles=profiles)
            attack_index = next(i for i, event in enumerate(result.log) if event['type'] == 'ram_attack')
            attack = result.log[attack_index]
            if -4 <= attack['attacker_health_after'] <= 0:
                later = result.log[attack_index + 1:]
                heal_index = next(i for i, event in enumerate(later)
                                  if event['type'] == 'heal' and event['actor'] == 'A')
                self.assertFalse(any(event.get('actor') == 'A' and event.get('type') in
                                     ('movement', 'attack', 'ram_attack', 'reaction_spent')
                                     for event in later[:heal_index]))
                self.assertGreater(result.final_health[0], 0)
                self.assertFalse(any(event['type'] == 'incapacity_dead' for event in result.log))
                self.assertEqual(self.audit(duel, result, profiles), [])
                found = True
                break
        self.assertTrue(found)

    def test_bleeding_that_kills_before_healing_cannot_be_reversed_by_healing_factor(self):
        duel = RamIncapacityDuel(self.profiles, self.policies, self_damage_mode='lethal_impact',
                                 initial_prone=(False, False), seed=1, initial_distance=1,
                                 max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS,
                                 end_turn_healing_first=False)
        duel.fighters[0].bleeding = 5
        duel._end_turn_effects(0)
        self.assertEqual(duel.fighters[0].health, -4)
        self.assertEqual([event['type'] for event in duel.log],
                         ['incapacity_contract', 'condition_tick', 'incapacity_dead'])

    def test_healing_and_bleeding_order_remains_an_explicit_variant(self):
        profiles = (replace(self.profiles[0], max_health=20), self.profiles[1])
        for healing_first, expected in ((True, 8), (False, 3)):
            with self.subTest(healing_first=healing_first):
                duel = RamIncapacityDuel(profiles, self.policies, self_damage_mode='lethal_impact',
                                         initial_prone=(False, False), seed=1, initial_distance=1,
                                         max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS,
                                         end_turn_healing_first=healing_first)
                duel.fighters[0].health = 3
                duel.fighters[0].bleeding = 5
                duel._end_turn_effects(0)
                self.assertEqual(duel.fighters[0].health, expected)
                self.assertEqual(duel.fighters[0].bleeding, 0)
