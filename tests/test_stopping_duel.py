from dataclasses import replace
from copy import deepcopy
import unittest

from blacklight.engine import Action, IllegalAction, Profile
from combatants.actions import DEFAULT_ACTIONS
from experimental.stopping_duel import StoppingDuel, StoppingPolicy
from experimental.stopping_audit import audit_stopping_duel
from experimental.parry_duel import ParryDuel
from blacklight.audit import audit_profiled_log
from tests.test_double_tap_duel import FixedDice


def fixture(*, focus=90, shield=False, followup=True):
    shooter = Profile('Shooter', 3, 300, 90, 4, 5, 3, 2, 14, 15, 6, ranged_range=10,
                      ranged_bonus=2, ranged_is_ammunition=True,
                      powers=frozenset({'accuracy', 'double_tap', 'stopping_power'}))
    target = Profile('Target', 3, 300, 90, 3, 3, 3, 1, 13, 13, 5,
                     weapons=frozenset({'shield'}) if shield else frozenset(), heroic=True)
    policies = (StoppingPolicy('shooter', prefer_stopping=True, use_stopping_followup=followup,
                               use_ram=False),
                StoppingPolicy('target', shield_react=shield, use_ram=False, always_wait=True))
    duel = StoppingDuel((shooter, target), policies, initial_prone=(False, False), seed=1,
                        initial_distance=1, max_rounds=3, audit=True,
                        ranged_weapons=('submachine_gun', 'generic'), action_registry=DEFAULT_ACTIONS)
    duel.round = 1
    duel._reset_reactions_for_round()
    duel.active_actor = 0
    duel.fighters[0].standard_available = True
    duel.fighters[0].focus = focus
    return duel


class StoppingDuelTests(unittest.TestCase):
    def test_fantastic_gets_independent_second_attack_for_single_focus_cost(self):
        duel = fixture()
        duel.rng = FixedDice((6, 1, 6, 6, 6, 6, 6))
        duel.damage_rng = FixedDice((3,) * 40)
        duel._act(0, Action('stopping_power'))
        attacks = [e for e in duel.log if e['type'] == 'attack']
        self.assertEqual([e['stopping_role'] for e in attacks], ['initial', 'followup'])
        self.assertEqual([e['calculated_damage'] for e in attacks], [40, 20])
        self.assertNotEqual(attacks[0]['trigger'], attacks[1]['trigger'])
        self.assertEqual((duel.fighters[0].focus, duel.fighters[1].health), (85, 240))
        self.assertEqual(sum(e['type'] == 'focus_spent' for e in duel.log), 1)

    def test_defensive_shield_blocks_both_ammunition_attacks(self):
        duel = fixture(shield=True)
        duel.rng = FixedDice((6, 1, 6, 6, 6, 6, 6))
        duel.damage_rng = FixedDice((3,) * 40)
        duel._act(0, Action('stopping_power'))
        attacks = [e for e in duel.log if e['type'] == 'attack']
        self.assertEqual(len(attacks), 2)
        self.assertTrue(all(e['ammunition_immunity'] and e['damage'] == 0 for e in attacks))
        self.assertEqual(duel.fighters[1].health, 300)

    def test_normal_hit_or_miss_never_grants_followup(self):
        for rolls, hit in (((6, 6, 6, 6), True), ((2, 2, 2, 2), False)):
            duel = fixture()
            duel.rng = FixedDice(rolls)
            duel.damage_rng = FixedDice((3,) * 40)
            duel._act(0, Action('stopping_power'))
            attacks = [e for e in duel.log if e['type'] == 'attack']
            self.assertEqual((len(attacks), attacks[0]['success']), (1, hit))
            self.assertFalse(next(e for e in duel.log if e['type'] == 'stopping_decision')['eligible'])

    def test_player_can_decline_followup(self):
        duel = fixture(followup=False)
        duel.rng = FixedDice((6, 1, 6))
        duel.damage_rng = FixedDice((3,) * 30)
        duel._act(0, Action('stopping_power'))
        self.assertEqual(sum(e['type'] == 'attack' for e in duel.log), 1)
        decision = next(e for e in duel.log if e['type'] == 'stopping_decision')
        self.assertEqual((decision['eligible'], decision['used']), (True, False))

    def test_incapacitated_target_does_not_receive_automatic_followup(self):
        duel = fixture()
        duel.fighters[1].profile = replace(duel.fighters[1].profile, max_health=1)
        duel.fighters[1].health = 1
        duel.rng = FixedDice((6, 1, 6))
        duel.damage_rng = FixedDice((3,) * 30)
        duel._act(0, Action('stopping_power'))
        self.assertEqual(sum(e['type'] == 'attack' for e in duel.log), 1)
        decision = next(e for e in duel.log if e['type'] == 'stopping_decision')
        self.assertEqual((decision['eligible'], decision['used']), (False, False))

    def test_focus_floor_and_prerequisites(self):
        duel = fixture(focus=5)
        self.assertNotIn(Action('stopping_power'), duel.legal_actions(0))
        with self.assertRaises(IllegalAction):
            duel._act(0, Action('stopping_power'))
        duel = fixture(focus=6)
        duel.rng = FixedDice((2, 2, 2, 2))
        duel.damage_rng = FixedDice((3,) * 30)
        duel._act(0, Action('stopping_power'))
        self.assertEqual(duel.fighters[0].focus, 1)
        p = replace(duel.fighters[0].profile, powers=frozenset({'stopping_power'}))
        with self.assertRaises(ValueError):
            StoppingDuel((p, duel.fighters[1].profile), duel.policies,
                         seed=1, audit=True, ranged_weapons=('submachine_gun', 'generic'))

    def test_previous_duel_replays_without_stopping_power(self):
        duel = fixture()
        profiles = (replace(duel.fighters[0].profile,
                            powers=duel.fighters[0].profile.powers - {'stopping_power'}),
                    duel.fighters[1].profile)
        policies = tuple(duel.policies)
        args = dict(initial_prone=(False, False), initial_distance=1, max_rounds=3, audit=True,
                    ranged_weapons=('submachine_gun', 'generic'), action_registry=DEFAULT_ACTIONS)
        for seed in range(20):
            self.assertEqual(StoppingDuel(profiles, policies, seed=seed, **args).run(),
                             ParryDuel(profiles, policies, seed=seed, **args).run())

    def test_full_duels_audit_stopping_and_point_blank_parry(self):
        duel = fixture()
        defender = replace(duel.fighters[1].profile, agility=5, agility_defense=15, run_speed=6,
                           ranged_range=10, ranged_bonus=2, ranged_is_ammunition=True,
                           powers=frozenset({'accuracy', 'point_blank_parry', 'fast_hands'}))
        profiles = (duel.fighters[0].profile, defender)
        policies = (duel.policies[0], replace(duel.policies[1], always_wait=False))
        weapons = ('submachine_gun', 'submachine_gun')
        observed = set()
        for seed in range(80):
            result = StoppingDuel(profiles, policies, seed=seed, initial_prone=(False, False),
                                  initial_distance=1, max_rounds=5, audit=True,
                                  ranged_weapons=weapons, action_registry=DEFAULT_ACTIONS).run()
            self.assertEqual(audit_stopping_duel(result, profiles, ranged_weapons=weapons,
                             initial_prone=(False, False), initial_distance=1, expected_seed=seed,
                             max_rounds=5, ruleset=StoppingDuel.table_ruleset), [])
            if seed == 0:
                start = next(i for i, event in enumerate(result.log) if event['type'] == 'stopping_start')
                decision = next(i for i in range(start + 1, len(result.log))
                                if result.log[i]['type'] == 'stopping_decision')
                self.assertTrue(any(event['type'] == 'parry_start' for event in result.log[start:decision]))
            for event in result.log:
                if event['type'] in ('stopping_start', 'parry_start'):
                    observed.add(event['type'])
                if event.get('stopping_role') == 'followup':
                    observed.add('followup')
        self.assertEqual(observed, {'stopping_start', 'parry_start', 'followup'})

    def test_auditor_rejects_forged_cost_eligibility_or_followup(self):
        duel = fixture()
        profiles, policies = tuple(f.profile for f in duel.fighters), tuple(duel.policies)
        args = dict(initial_prone=(False, False), initial_distance=1, max_rounds=4, audit=True,
                    ranged_weapons=('submachine_gun', 'generic'), action_registry=DEFAULT_ACTIONS)
        result = None
        for seed in range(100):
            candidate = StoppingDuel(profiles, policies, seed=seed, **args).run()
            if any(e.get('stopping_role') == 'followup' for e in candidate.log):
                result = candidate
                break
        self.assertIsNotNone(result)
        context = dict(ranged_weapons=args['ranged_weapons'], initial_prone=(False, False),
                       initial_distance=1, expected_seed=seed, max_rounds=4, ruleset=StoppingDuel.table_ruleset)
        self.assertEqual(audit_stopping_duel(result, profiles, **context), [])
        self.assertTrue(audit_profiled_log(result.log, profiles, ruleset=StoppingDuel.table_ruleset,
                                           allow_experimental_parry=True))
        for kind, field, value in (('focus_spent', 'amount', 4),
                                   ('stopping_decision', 'trigger', 999),
                                   ('stopping_end', 'followed_up', False)):
            log = deepcopy(result.log)
            index = next(i for i, event in enumerate(log) if event['type'] == kind
                         and (kind != 'focus_spent' or event.get('source') == 'stopping_power')
                         and (kind != 'stopping_end' or event.get('followed_up') is True))
            log[index][field] = value
            self.assertTrue(audit_stopping_duel(replace(result, log=log), profiles, **context))
        log = deepcopy(result.log)
        followup = next(event for event in log if event.get('stopping_role') == 'followup')
        followup['stopping_use_id'] = 999
        self.assertTrue(audit_stopping_duel(replace(result, log=log), profiles, **context))
