from copy import deepcopy
from dataclasses import replace
import unittest

from blacklight.engine import Action, Profile, blacklight_profile
from combatants.actions import DEFAULT_ACTIONS
from experimental.double_tap_duel import DoubleTapDuel
from experimental.ranged_powers_duel import RangedPowersDuel, RangedPowersPolicy
from experimental.ranged_powers_audit import audit_ranged_powers_duel
from tests.test_double_tap_duel import FixedDice


def fixture(*, prone=False, shield=False, dodge=True, brawling=False):
    shooter = Profile('Atirador', 3, 300, 90, 4, 5, 3, 2, 14, 15, 6,
                      ranged_range=10, ranged_bonus=2, ranged_is_ammunition=True,
                      powers=frozenset({'accuracy', 'double_tap', 'slow_motion_dodge'}))
    powers = {'slow_motion_dodge'} | ({'brawling'} if brawling else set())
    target = Profile('Defensor', 3, 300, 90, 3, 3, 3, 1, 13, 13, 5,
                     powers=frozenset(powers), traits=frozenset({'combat_reflexes'}),
                     weapons=frozenset({'shield'}) if shield else frozenset(), heroic=True)
    policies = (RangedPowersPolicy('atirador', use_ram=False),
                RangedPowersPolicy('defensor', use_ram=False, always_wait=True,
                                   stand_when_prone=False, shield_react=shield,
                                   dodge_agility_attacks=dodge))
    args = dict(initial_prone=(False, prone), seed=1, initial_distance=1,
                max_rounds=4, audit=True, action_registry=DEFAULT_ACTIONS)
    return (shooter, target), policies, args


class RangedPowersTests(unittest.TestCase):
    def test_two_powers_prone_and_audited_full_duels(self):
        profiles, policies, args = fixture(prone=True)
        found = set()
        for seed in range(60):
            args['seed'] = seed
            result = RangedPowersDuel(profiles, policies, **args).run()
            self.assertEqual(audit_ranged_powers_duel(result, profiles,
                             initial_prone=args['initial_prone'], initial_distance=1,
                             expected_seed=seed, max_rounds=4,
                             ruleset=RangedPowersDuel.table_ruleset), [])
            for event in result.log:
                if event['type'] == 'attack' and event['actor'] == 'Atirador':
                    if event['troubles'] == 2:
                        found.add('prone_and_slow')
                    if event['success'] and event['fantastic']:
                        found.add('fantastic')
                if event['type'] == 'double_tap_end':
                    found.add('double_tap')
                if event['type'] == 'slow_motion_dodge':
                    found.add('slow_dodge')
        self.assertEqual(found, {'prone_and_slow', 'fantastic', 'double_tap', 'slow_dodge'})

    def test_same_attack_cannot_spend_two_reactions_on_slow_and_shield(self):
        for dodge in (True, False):
            profiles, policies, args = fixture(shield=True, dodge=dodge)
            duel = RangedPowersDuel(profiles, policies, **args)
            duel.round = 1
            duel._reset_reactions_for_round()
            duel.active_actor = 0
            duel.fighters[0].standard_available = True
            duel.rng = FixedDice((6, 6, 6, 6))
            duel.damage_rng = FixedDice((3,) * 30)
            duel._act(0, Action('double_tap'))
            event_types = [event['type'] for event in duel.log]
            if dodge:
                self.assertIn('slow_motion_dodge', event_types)
                self.assertNotIn('shield_activate', event_types)
                self.assertEqual(duel.fighters[1].reactions, 1)
            else:
                self.assertNotIn('slow_motion_dodge', event_types)
                self.assertIn('shield_activate', event_types)
                self.assertEqual(duel.fighters[1].reactions, 1)

    def test_brawling_blocks_slow_dodge_even_against_double_tap(self):
        profiles, policies, args = fixture(brawling=True)
        result = RangedPowersDuel(profiles, policies, **args).run()
        self.assertFalse(any(e['type'] == 'slow_motion_dodge' and e['actor'] == 'Defensor'
                             for e in result.log))
        self.assertEqual(audit_ranged_powers_duel(result, profiles, initial_prone=(False, False),
                         initial_distance=1, expected_seed=1, max_rounds=4,
                         ruleset=RangedPowersDuel.table_ruleset), [])

    def test_victor_can_fight_opponent_with_both_powers(self):
        profiles, policies, args = fixture()
        profiles = (profiles[0], blacklight_profile())
        policies = (policies[0], replace(policies[1], always_wait=False, weapon='hammer',
                    offhand='blade', prefer_fast=True, effect_limb=1))
        args.update(initial_distance=2, max_rounds=6)
        result = RangedPowersDuel(profiles, policies, **args).run()
        self.assertTrue(any(e['type'] == 'fast_use_start' for e in result.log))
        self.assertEqual(audit_ranged_powers_duel(result, profiles, initial_prone=(False, False),
                         initial_distance=2, expected_seed=1, max_rounds=6,
                         ruleset=RangedPowersDuel.table_ruleset), [])

    def test_ram_prone_and_slow_dodge_share_audited_reaction_budgets(self):
        profiles, policies, args = fixture()
        policies = (policies[0], replace(policies[1], always_wait=False, use_ram=True))
        args.update(seed=3, initial_distance=11, max_rounds=6)
        result = RangedPowersDuel(profiles, policies, **args).run()
        self.assertTrue({'ram_attack', 'prone_start', 'slow_motion_dodge'} <=
                        {event['type'] for event in result.log})
        self.assertEqual(audit_ranged_powers_duel(result, profiles, initial_prone=(False, False),
                         initial_distance=11, expected_seed=3, max_rounds=6,
                         ruleset=RangedPowersDuel.table_ruleset), [])

    def test_unmodified_double_tap_replays_without_slow_power(self):
        profiles, policies, args = fixture()
        profiles = tuple(replace(p, powers=p.powers - {'slow_motion_dodge'}) for p in profiles)
        for seed in range(15):
            args['seed'] = seed
            self.assertEqual(RangedPowersDuel(profiles, policies, **args).run(),
                             DoubleTapDuel(profiles, policies, **args).run())

    def test_forged_slow_dodge_or_missing_marker_fails_audit(self):
        profiles, policies, args = fixture(prone=True)
        result = RangedPowersDuel(profiles, policies, **args).run()
        index = next(i for i, event in enumerate(result.log) if event['type'] == 'slow_motion_dodge')
        context = dict(initial_prone=(False, True), initial_distance=1, expected_seed=1,
                       max_rounds=4, ruleset=RangedPowersDuel.table_ruleset)
        for field, value in (('trigger', 999), ('before_roll', False), ('added_troubles', 2)):
            log = deepcopy(result.log)
            log[index][field] = value
            self.assertTrue(audit_ranged_powers_duel(replace(result, log=log), profiles, **context))
        log = list(deepcopy(result.log))
        log.pop(index)
        for i, event in enumerate(log, 1):
            event['seq'] = i
        self.assertTrue(audit_ranged_powers_duel(replace(result, log=tuple(log)), profiles, **context))
