from dataclasses import asdict, replace
from copy import deepcopy
import json
from pathlib import Path
import unittest

from blacklight.engine import IllegalAction, Move, Profile
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.sheets import load_sheet
from experimental.crossbones_subset import build_crossbones_stopping_subset
from experimental.stopping_audit import audit_stopping_duel
from experimental.stopping_duel import StoppingPolicy
from experimental.stopping_ram_duel import StoppingRamDuel

ROOT = Path(__file__).resolve().parents[1]
MODE = 'stop_before_heal_reject_lethal'


class StationaryPolicy(StoppingPolicy):
    def choose_move(self, observation):
        return Move()


def boundary(*, attacker_health=20, target_health=250):
    attacker = Profile('Atacante sintético', 3, attacker_health, 60, 4, 0, 5, 2, 14, 10, 5,
                       initiative_modifier=100, powers=frozenset({'healing_factor'}))
    target = Profile('Alvo sintético', 3, target_health, 60, 2, 0, 5, 2, 12, 10, 5,
                     initiative_modifier=0)
    policies = (StoppingPolicy('atacante'), StationaryPolicy('alvo', always_wait=True, use_ram=False))
    args = dict(seed=1, initial_prone=(False, False), initial_distance=10, max_rounds=1, audit=True,
                ranged_weapons=('generic', 'generic'), action_registry=DEFAULT_ACTIONS,
                stop_on_attacker=attacker.name)
    return (attacker, target), policies, args


class StoppingRamDuelTests(unittest.TestCase):
    def test_current_ram_ruling_is_audited_with_full_host(self):
        profiles, policies, args = boundary()
        result = StoppingRamDuel(profiles, policies, **args).run()
        self.assertEqual((result.final_health, result.outcome), ((-1, 210), 'win'))
        self.assertTrue(any(event['type'] == 'ram_incapacity_stop' for event in result.log))
        self.assertFalse(any(event['type'] == 'heal' and event['actor'] == profiles[0].name
                             for event in result.log))
        self.assertEqual(audit_stopping_duel(result, profiles, ranged_weapons=args['ranged_weapons'],
                         initial_prone=(False, False), initial_distance=10, expected_seed=1, max_rounds=1,
                         ruleset=StoppingRamDuel.table_ruleset, self_damage_mode=MODE,
                         stop_on_attacker=profiles[0].name), [])
        self.assertEqual(result, StoppingRamDuel(profiles, policies, **args).run())
        forged = deepcopy(result.log)
        next(event for event in forged if event['type'] == 'ram_incapacity_stop')['health'] = 0
        self.assertTrue(audit_stopping_duel(replace(result, log=forged), profiles,
                        ranged_weapons=args['ranged_weapons'], initial_prone=(False, False),
                        initial_distance=10, expected_seed=1, max_rounds=1,
                        ruleset=StoppingRamDuel.table_ruleset, self_damage_mode=MODE,
                        stop_on_attacker=profiles[0].name))

    def test_previous_table_ruling_example_is_preserved(self):
        profiles, policies, args = boundary()
        result = StoppingRamDuel(profiles, policies, **args).run()
        expected = json.loads((ROOT / 'experimental_outputs/ram_stop_table_ruling_001.json')
                              .read_text(encoding='utf-8'))['result']
        actual = json.loads(json.dumps(asdict(result), default=sorted))
        self.assertEqual(actual, expected)

    def test_both_unconscious_are_draw_and_death_boundary_still_aborts(self):
        profiles, policies, args = boundary(target_health=1)
        result = StoppingRamDuel(profiles, policies, **args).run()
        self.assertEqual((result.final_health, result.outcome, result.winner), ((-1, 0), 'draw', None))
        self.assertEqual(audit_stopping_duel(result, profiles, ranged_weapons=args['ranged_weapons'],
                         initial_prone=(False, False), initial_distance=10, expected_seed=1, max_rounds=1,
                         ruleset=StoppingRamDuel.table_ruleset, self_damage_mode=MODE,
                         stop_on_attacker=profiles[0].name), [])
        profiles, policies, args = boundary(attacker_health=1)
        with self.assertRaisesRegex(IllegalAction, 'death threshold is undecided'):
            StoppingRamDuel(profiles, policies, **args).run()

    def test_victor_ram_and_ranged_powers_are_audited_together(self):
        evidence = json.loads((ROOT / 'character_evidence/crossbones_core_p155.json').read_text(encoding='utf-8'))
        subset = build_crossbones_stopping_subset(evidence, accept_incomplete=True)
        victor = compile_duel(load_sheet(ROOT / 'characters/victor_halle/rank3_2026-10-27_split_fast.json'))
        profiles = (subset.profile, victor)
        policies = (StoppingPolicy('crossbones parcial', prefer_stopping=True, use_ram=False),
                    StoppingPolicy('victor', weapon='hammer', offhand='blade', prefer_fast=True,
                                   effect_limb=1, use_ram=True, shield_react=True))
        args = dict(seed=28, initial_prone=(False, False), initial_distance=10, max_rounds=8,
                    audit=True, ranged_weapons=('submachine_gun', 'generic'),
                    action_registry=DEFAULT_ACTIONS, stop_on_attacker='Blacklight')
        result = StoppingRamDuel(profiles, policies, **args).run()
        self.assertTrue({'ram_attack', 'stopping_start', 'parry_start'} <=
                        {event['type'] for event in result.log})
        self.assertEqual(audit_stopping_duel(result, profiles, ranged_weapons=args['ranged_weapons'],
                         initial_prone=(False, False), initial_distance=10, expected_seed=28, max_rounds=8,
                         ruleset=StoppingRamDuel.table_ruleset, self_damage_mode=MODE,
                         stop_on_attacker='Blacklight'), [])
        self.assertEqual(result, StoppingRamDuel(profiles, policies, **args).run())
        args['seed'] = 45
        result = StoppingRamDuel(profiles, policies, **args).run()
        missed_ram = {event['trigger'] for event in result.log if event['type'] == 'ram_attack'
                      and not event['transaction']['parameters']['success']}
        self.assertTrue(any(event['type'] == 'parry_start' and event['source_trigger'] in missed_ram
                            for event in result.log))
        self.assertEqual(audit_stopping_duel(result, profiles, ranged_weapons=args['ranged_weapons'],
                         initial_prone=(False, False), initial_distance=10, expected_seed=45, max_rounds=8,
                         ruleset=StoppingRamDuel.table_ruleset, self_damage_mode=MODE,
                         stop_on_attacker='Blacklight'), [])

    def test_enemy_parry_damage_is_not_misclassified_as_ram_self_damage(self):
        attacker = Profile('A', 3, 15, 60, 0, 0, 5, 2, 10, 10, 5, initiative_modifier=100,
                           powers=frozenset({'healing_factor'}))
        defender = Profile('B', 3, 250, 90, 4, 5, 3, 2, 14, 15, 6, ranged_range=10,
                           ranged_bonus=2, ranged_is_ammunition=True,
                           powers=frozenset({'accuracy', 'point_blank_parry', 'fast_hands'}))
        profiles = (attacker, defender)
        policies = (StoppingPolicy('A'), StationaryPolicy('B', always_wait=True, use_ram=False))
        weapons = ('generic', 'submachine_gun')
        args = dict(seed=0, initial_prone=(False, False), initial_distance=10, max_rounds=1, audit=True,
                    ranged_weapons=weapons, action_registry=DEFAULT_ACTIONS, stop_on_attacker='A')
        result = StoppingRamDuel(profiles, policies, **args).run()
        ram = next(event for event in result.log if event['type'] == 'ram_attack')
        parry = next(event for event in result.log if event.get('reaction_power') == 'point_blank_parry')
        self.assertFalse(ram['transaction']['parameters']['success'])
        self.assertEqual(ram['attacker_health_after'], 15)
        self.assertEqual(parry['health_after'], -11)
        self.assertFalse(any(event['type'] == 'ram_incapacity_stop' for event in result.log))
        self.assertTrue(any(event['type'] == 'heal' and event['actor'] == 'A' for event in result.log))
        self.assertEqual(audit_stopping_duel(result, profiles, ranged_weapons=weapons,
                         initial_prone=(False, False), initial_distance=10, expected_seed=0, max_rounds=1,
                         ruleset=StoppingRamDuel.table_ruleset, self_damage_mode=MODE,
                         stop_on_attacker='A'), [])
