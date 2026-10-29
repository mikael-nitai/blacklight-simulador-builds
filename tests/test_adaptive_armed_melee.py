from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from blacklight.engine import Action, IllegalAction, Move
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.sheets import load_sheet
from experimental.adaptive_armed_melee import DeclaredArmedMeleeDuel, ShieldAwarePolicy
from experimental.adaptive_armed_melee_audit import audit_declared_armed_melee
from experimental.crossbones_subset import build_crossbones_stopping_subset
from experimental.stopping_duel import StoppingPolicy
from experimental.stopping_ram_duel import StoppingRamDuel
from scripts.crossbones_ram_demo import EVIDENCE, VICTOR
from scripts.adaptive_armed_melee_demo import run as run_demo
from tests.test_nonlethal_ram_duel import profile


class MeleePolicy(StoppingPolicy):
    def choose_move(self, observation):
        return Move()

    def choose_action(self, observation):
        return Action('melee')


class AdaptiveArmedMeleeTests(unittest.TestCase):
    def crossbones_case(self, seed=3):
        evidence = json.loads(EVIDENCE.read_text(encoding='utf-8'))
        subset = build_crossbones_stopping_subset(evidence, accept_incomplete=True)
        profiles = (subset.profile, compile_duel(load_sheet(VICTOR)))
        policies = (ShieldAwarePolicy('crossbones', prefer_stopping=True, use_ram=False,
                                      treat_bleeding=True, kite=True, move_after_attack=True),
                    StoppingPolicy('victor', weapon='hammer', shield_react=True, use_ram=False))
        weapons = (subset.ranged_weapon, 'generic')
        duel = DeclaredArmedMeleeDuel(profiles, policies, seed=seed, initial_prone=(False, False),
                    initial_distance=10, max_rounds=10, audit=True, action_registry=DEFAULT_ACTIONS,
                    ranged_weapons=weapons, stop_on_attacker=profiles[1].name,
                    declared_armed_lethal=(profiles[0].name,))
        return duel, duel.run(), profiles, weapons

    def audit_case(self, result, profiles, weapons, *, seed=3):
        return audit_declared_armed_melee(result, profiles, declared_armed_lethal=(profiles[0].name,),
                    ranged_weapons=weapons, initial_prone=(False, False), initial_distance=10,
                    expected_seed=seed, max_rounds=10, ruleset='split_fast_v3',
                    self_damage_mode='stop_before_heal_reject_lethal', stop_on_attacker=profiles[1].name)

    def test_crossbones_switches_from_ammunition_to_declared_melee(self):
        duel, result, profiles, weapons = self.crossbones_case()
        self.assertEqual(self.audit_case(result, profiles, weapons), [])
        self.assertEqual(result, self.crossbones_case()[1])
        declarations = [e for e in result.log if e['type'] == 'lethality_declaration']
        attacks = [e for e in result.log if e['type'] == 'attack' and e.get('declared_lethality') == 'lethal']
        self.assertTrue(declarations and attacks)
        self.assertLess(declarations[0]['seq'], attacks[0]['seq'])
        self.assertEqual((attacks[0]['actor'], attacks[0]['mode'], attacks[0]['distance']),
                         (profiles[0].name, 'melee', 1))
        self.assertTrue(any(e['type'] == 'shield_activate' and e['actor'] == profiles[1].name
                            and e['seq'] < declarations[0]['seq'] for e in result.log))

    def test_policy_changes_only_after_observing_active_shield(self):
        duel, _, _, _ = self.crossbones_case()
        policy = duel.policies[0]
        duel.distance = 5
        duel.fighters[1].shield_active = False
        self.assertEqual(policy.choose_action(duel.observe(0)).kind, 'stopping_power')
        duel.fighters[1].shield_active = True
        observation = duel.observe(0)
        self.assertEqual(policy.choose_move(observation), Move('approach', 4))
        self.assertEqual(policy.choose_action(observation), Action('move', move=Move('approach', 4)))
        duel.distance = 1
        self.assertEqual(policy.choose_action(duel.observe(0)), Action('melee'))

    def test_tampering_with_declaration_or_attack_is_detected(self):
        _, result, profiles, weapons = self.crossbones_case()
        index = next(i for i, e in enumerate(result.log) if e['type'] == 'lethality_declaration')
        attack = next(i for i, e in enumerate(result.log) if e.get('declared_lethality') == 'lethal')
        for item, field, value in ((index, 'choice', 'nonlethal'), (index, 'actor', profiles[1].name),
                                   (attack, 'declared_lethality', 'nonlethal'), (index, 'seq', True)):
            with self.subTest(field=field):
                rows = deepcopy(list(result.log))
                rows[item][field] = value
                self.assertTrue(self.audit_case(replace(result, log=tuple(rows)), profiles, weapons))
        rows = deepcopy(list(result.log))
        rows[index]['type'] = 'turn_end'
        self.assertTrue(self.audit_case(replace(result, log=tuple(rows)), profiles, weapons))

    def test_only_explicit_actor_can_resolve_armed_bare_attack(self):
        attacker = profile('A', 4, initiative=100, ranged_range=10)
        victim = profile('B', 2, health=1)
        profiles = (attacker, victim)
        policies = (MeleePolicy('A', use_ram=False), StoppingPolicy('B', always_wait=True, use_ram=False))
        arguments = dict(seed=1, initial_distance=1, max_rounds=1, audit=True,
                         action_registry=DEFAULT_ACTIONS, ranged_weapons=('generic', 'generic'),
                         stop_on_attacker='B')
        with self.assertRaisesRegex(IllegalAction, 'armed profile'):
            StoppingRamDuel(profiles, policies, **arguments).run()
        with self.assertRaisesRegex(IllegalAction, 'armed profile'):
            DeclaredArmedMeleeDuel(profiles, policies, declared_armed_lethal=(), **arguments).run()
        duel = DeclaredArmedMeleeDuel(profiles, policies, declared_armed_lethal=('A',), **arguments)
        result = duel.run()
        self.assertLessEqual(result.final_health[1], -victim.max_health)
        self.assertEqual(audit_declared_armed_melee(result, profiles, declared_armed_lethal=('A',),
                         ranged_weapons=('generic', 'generic'), initial_prone=(False, False),
                         initial_distance=1, expected_seed=1, max_rounds=1, ruleset='split_fast_v3',
                         self_damage_mode='stop_before_heal_reject_lethal', stop_on_attacker='B'), [])
        with self.assertRaises(ValueError):
            DeclaredArmedMeleeDuel(profiles, policies, declared_armed_lethal=('B',), **arguments)

    def test_demo_is_audited_and_refuses_to_overwrite(self):
        with TemporaryDirectory() as directory, \
                patch('scripts.adaptive_armed_melee_demo.source_commit', return_value='test'):
            output = Path(directory) / 'demo.json'
            run_demo(output)
            contents = output.read_bytes()
            data = json.loads(contents)
            self.assertEqual(data['audit_issues'], [])
            self.assertEqual(data['declared_armed_lethal'], ['Crossbones (recorte experimental)'])
            self.assertTrue(any(e.get('declared_lethality') == 'lethal' for e in data['result']['log']))
            with self.assertRaises((FileExistsError, ValueError)):
                run_demo(output)
            self.assertEqual(output.read_bytes(), contents)


if __name__ == '__main__':
    unittest.main()
