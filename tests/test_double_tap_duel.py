from dataclasses import replace
from copy import deepcopy
import unittest

from blacklight.engine import Action, IllegalAction, Profile, blacklight_profile
from combatants.actions import DEFAULT_ACTIONS
from experimental.double_tap_duel import DoubleTapDuel, DoubleTapPolicy
from experimental.double_tap_audit import audit_double_tap_duel
from experimental.nonlethal_ram_duel import NonlethalRamProneDuel


class FixedDice:
    def __init__(self, faces):
        self.faces = iter(faces)

    def randint(self, low, high):
        face = next(self.faces)
        assert low <= face <= high
        return face


def setup_duel(*, distance=2, shield=False, ammunition=True, hit=(6, 1, 6), power=True):
    attacker = Profile('Atirador sintetico', 3, 90, 90, 4, 5, 3, 2, 14, 15, 6,
                       ranged_range=10, ranged_bonus=2, ranged_is_ammunition=ammunition,
                       powers=frozenset({'accuracy', 'double_tap'} if power else {'accuracy'}))
    victor = replace(blacklight_profile(), shield_active=shield)
    policies = (DoubleTapPolicy('atirador', use_ram=False),
                DoubleTapPolicy('victor', use_ram=False))
    duel = DoubleTapDuel((attacker, victor), policies, initial_prone=(False, False),
                         seed=1, initial_distance=distance, max_rounds=1, audit=True,
                         action_registry=DEFAULT_ACTIONS)
    duel.round = 1
    duel._reset_reactions_for_round()
    duel.active_actor = 0
    duel.fighters[0].standard_available = True
    duel.rng = FixedDice(hit)
    duel.damage_rng = FixedDice((3,) * 30)
    return duel


class DoubleTapDuelTests(unittest.TestCase):
    def test_fantastic_regular_ranged_damage_doubles_and_causes_bleeding(self):
        duel = setup_duel()
        self.assertIn(Action('double_tap'), duel.legal_actions(0))
        duel._act(0, Action('double_tap'))
        attack = next(e for e in duel.log if e['type'] == 'attack')
        self.assertEqual(attack['target_number'], 16)  # Victor's Brawling redirects to Melee
        self.assertEqual((attack['success'], attack['fantastic'], attack['calculated_damage']),
                         (True, True, 34))  # (4d6 + 5) * 2 after Sturdy 1
        self.assertEqual(duel.fighters[1].bleeding, 5)
        self.assertFalse(duel.fighters[0].standard_available)

    def test_shield_ammunition_immunity_prevents_damage_and_bleeding(self):
        duel = setup_duel(shield=True)
        duel._act(0, Action('double_tap'))
        attack = next(e for e in duel.log if e['type'] == 'attack')
        self.assertTrue(attack['ammunition_immunity'])
        self.assertEqual((attack['damage'], duel.fighters[1].bleeding), (0, 0))

    def test_normal_hit_or_miss_never_causes_bleeding(self):
        for faces, hit in (((6, 6, 6), True), ((2, 2, 2), False)):
            with self.subTest(faces=faces):
                duel = setup_duel(hit=faces)
                duel._act(0, Action('double_tap'))
                attack = next(e for e in duel.log if e['type'] == 'attack')
                self.assertEqual(attack['success'], hit)
                self.assertEqual(duel.fighters[1].bleeding, 0)

    def test_outside_range_or_without_power_is_rejected(self):
        for duel in (setup_duel(distance=3), setup_duel(power=False)):
            self.assertNotIn(Action('double_tap'), duel.legal_actions(0))
            with self.assertRaises(IllegalAction):
                duel._act(0, Action('double_tap'))

    def test_regular_full_duel_is_reproducible(self):
        duel = setup_duel()
        args = dict(initial_prone=(False, False), seed=32, initial_distance=2,
                    max_rounds=5, audit=True, action_registry=DEFAULT_ACTIONS)
        profiles = tuple(f.profile for f in duel.fighters)
        policies = tuple(duel.policies)
        first = DoubleTapDuel(profiles, policies, **args).run()
        second = DoubleTapDuel(profiles, policies, **args).run()
        self.assertEqual(first, second)
        self.assertTrue(any(e['type'] == 'double_tap_start' for e in first.log))
        self.assertEqual(audit_double_tap_duel(first, profiles, initial_prone=(False, False),
                          initial_distance=2, expected_seed=32, max_rounds=5,
                          ruleset=DoubleTapDuel.table_ruleset), [])

    def test_audited_full_duels_cover_hit_miss_fantastic_and_reactive_shield(self):
        duel = setup_duel()
        profiles = tuple(f.profile for f in duel.fighters)
        policies = (duel.policies[0], replace(duel.policies[1], shield_react=True))
        observed = set()
        for seed in range(60):
            result = DoubleTapDuel(profiles, policies, initial_prone=(False, False), seed=seed,
                                   initial_distance=2, max_rounds=5, audit=True,
                                   action_registry=DEFAULT_ACTIONS).run()
            self.assertEqual(audit_double_tap_duel(result, profiles, initial_prone=(False, False),
                              initial_distance=2, expected_seed=seed, max_rounds=5,
                              ruleset=DoubleTapDuel.table_ruleset), [])
            for index, event in enumerate(result.log):
                if event['type'] == 'double_tap_end':
                    attack = next(e for e in reversed(result.log[:index]) if e['type'] == 'attack')
                    observed.add('fantastic' if attack['success'] and attack['fantastic'] else
                                 'hit' if attack['success'] else 'miss')
                if event['type'] == 'shield_activate' and event.get('cost') == 'reaction':
                    observed.add('shield')
        self.assertTrue({'miss', 'hit', 'fantastic', 'shield'} <= observed)

    def test_independent_audit_rejects_forged_transaction(self):
        duel = setup_duel()
        profiles = tuple(f.profile for f in duel.fighters)
        policies = (duel.policies[0], replace(duel.policies[1], always_wait=True))
        context = dict(initial_prone=(False, False), initial_distance=2,
                       max_rounds=3, ruleset=DoubleTapDuel.table_ruleset)
        result = None
        for seed in range(100):
            candidate = DoubleTapDuel(profiles, policies, initial_prone=(False, False),
                                      seed=seed, initial_distance=2, max_rounds=3, audit=True,
                                      action_registry=DEFAULT_ACTIONS).run()
            if any(e['type'] == 'double_tap_end' and e['bleeding'] for e in candidate.log):
                result = candidate
                break
        self.assertIsNotNone(result)
        self.assertEqual(audit_double_tap_duel(result, profiles, expected_seed=seed, **context), [])
        index = next(i for i, e in enumerate(result.log)
                     if e['type'] == 'condition_start' and 'CORE-P95-DOUBLE-TAP' in e['rules'])
        for field, value in (('trigger', 999), ('intensity', 10)):
            log = deepcopy(result.log)
            log[index][field] = value
            self.assertTrue(audit_double_tap_duel(replace(result, log=log), profiles,
                                                  expected_seed=seed, **context))
        log = list(deepcopy(result.log))
        log.pop(index)
        for seq, event in enumerate(log, 1):
            event['seq'] = seq
        self.assertTrue(audit_double_tap_duel(replace(result, log=tuple(log)), profiles,
                                              expected_seed=seed, **context))

    def test_full_victor_fast_and_healing_interactions(self):
        duel = setup_duel()
        shooter = replace(duel.fighters[0].profile, max_health=300)
        profiles = (shooter, duel.fighters[1].profile)
        policies = (duel.policies[0], replace(duel.policies[1], weapon='hammer',
                    offhand='blade', prefer_fast=True, effect_limb=1, shield_react=False))
        observed = set()
        for seed in range(80):
            result = DoubleTapDuel(profiles, policies, initial_prone=(False, False), seed=seed,
                                   initial_distance=2, max_rounds=8, audit=True,
                                   action_registry=DEFAULT_ACTIONS).run()
            self.assertEqual(audit_double_tap_duel(result, profiles, initial_prone=(False, False),
                              initial_distance=2, expected_seed=seed, max_rounds=8,
                              ruleset=DoubleTapDuel.table_ruleset), [])
            for event in result.log:
                if event['type'] == 'fast_use_start' and event['actor'] == profiles[1].name:
                    observed.add('fast')
                if (event['type'] == 'condition_start' and
                        'CORE-P95-DOUBLE-TAP' in event['rules']):
                    observed.add('bleeding')
                if (event['type'] == 'condition_end' and event.get('condition') == 'bleeding'
                        and event['actor'] == profiles[1].name):
                    observed.add('recovered')
        self.assertEqual(observed, {'fast', 'bleeding', 'recovered'})

    def test_profiles_without_power_preserve_existing_host_replay(self):
        duel = setup_duel(power=False)
        profiles = tuple(f.profile for f in duel.fighters)
        policies = tuple(duel.policies)
        for seed in range(20):
            args = dict(initial_prone=(False, False), seed=seed, initial_distance=2,
                        max_rounds=5, audit=True, action_registry=DEFAULT_ACTIONS)
            self.assertEqual(DoubleTapDuel(profiles, policies, **args).run(),
                             NonlethalRamProneDuel(profiles, policies, **args).run())
