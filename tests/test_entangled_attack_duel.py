from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from combatants.actions import DEFAULT_ACTIONS
from experimental.entangled_attack_audit import audit_entangled_attacks
from experimental.entangled_attack_duel import EntangledAttackDuel, EntangledAttackPolicy
from tests import test_grappling_duel as grapple_fixtures
from scripts.entangled_attack_demo import run as run_demo


class EntangledAttackDuelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        grapple_fixtures.GrapplingDuelTests.setUpClass()
        cls.profiles = grapple_fixtures.GrapplingDuelTests.profiles
        cls.weapons = grapple_fixtures.GrapplingDuelTests.weapons
        cls.policies = (EntangledAttackPolicy('crossbones', prefer_grapple=True, prefer_stopping=True,
                          use_ram=False, attack_when_grabbing=True),
                        EntangledAttackPolicy('victor', weapon='hammer', offhand='blade', prefer_fast=True,
                          shield_react=True, use_ram=False, escape_reaction=False, attack_when_grabbed=True))

    def run_case(self, seed, trouble):
        duel = EntangledAttackDuel(self.profiles, self.policies, seed=seed, initial_prone=(False, False),
            initial_distance=1, max_rounds=4, audit=True, action_registry=DEFAULT_ACTIONS,
            ranged_weapons=self.weapons, stop_on_attacker=self.profiles[1].name,
            declared_armed_lethal=(self.profiles[0].name,), escape_trigger_mode='attack',
            inside_attack_trouble=trouble)
        return duel, duel.run()

    def audit_case(self, result, seed, trouble):
        return audit_entangled_attacks(result, self.profiles, inside_attack_trouble=trouble,
            declared_armed_lethal=(self.profiles[0].name,), escape_trigger_mode='attack',
            ranged_weapons=self.weapons, initial_prone=(False, False), initial_distance=1,
            expected_seed=seed, max_rounds=4, ruleset='split_fast_v3',
            self_damage_mode='stop_before_heal_reject_lethal', stop_on_attacker=self.profiles[1].name)

    def test_replayed_duels_cover_pinned_two_arm_fast_and_holder_attacks(self):
        witnessed = set()
        for trouble in (False, True):
            for seed in range(50):
                with self.subTest(trouble=trouble, seed=seed):
                    _, result = self.run_case(seed, trouble)
                    self.assertEqual(result, self.run_case(seed, trouble)[1])
                    self.assertEqual(self.audit_case(result, seed, trouble), [])
                    checks = [e for e in result.log if e['type'] == 'entangled_attack_check']
                    for check in checks:
                        self.assertEqual(check['added_troubles'], int(check['pinned']) + int(trouble))
                        if check['pinned']:
                            witnessed.add('pinned')
                        if check['actor'] == self.profiles[0].name:
                            witnessed.add('holder')
                        if check['mode'] == 'blade_fast':
                            witnessed.add('fast_both_arms')
        self.assertEqual(witnessed, {'pinned', 'holder', 'fast_both_arms'})

    def test_pinned_fast_has_two_troubles_when_hypothesis_enabled(self):
        _, result = self.run_case(7, True)
        markers = [e for e in result.log if e['type'] == 'entangled_attack_check' and e['pinned']]
        self.assertEqual([e['mode'] for e in markers], ['hammer_fast', 'blade_fast'])
        self.assertTrue(all(e['added_troubles'] == 2 for e in markers))
        for e in markers:
            check = next(a for a in result.log if a['type'] == 'attack' and a['trigger'] == e['trigger'])
            self.assertEqual((check['edges'], check['troubles']), (2, 2))

    def test_independent_audit_rejects_forged_or_missing_modifier(self):
        _, result = self.run_case(7, True)
        index = next(i for i, e in enumerate(result.log) if e['type'] == 'entangled_attack_check')
        for field, value in (('added_troubles', 0), ('pinned', False), ('inside_attack_trouble', False),
                             ('trigger', 9999), ('target', self.profiles[1].name)):
            rows = deepcopy(list(result.log)); rows[index][field] = value
            self.assertTrue(self.audit_case(replace(result, log=tuple(rows)), 7, True), field)
        rows = deepcopy(list(result.log)); rows[index]['type'] = 'wait'
        self.assertTrue(self.audit_case(replace(result, log=tuple(rows)), 7, True))

    def test_example_is_audited_and_refuses_overwrite(self):
        with TemporaryDirectory() as directory, patch('scripts.entangled_attack_demo.source_commit', return_value='test'):
            output = Path(directory) / 'demo.json'
            run_demo(output)
            original = output.read_bytes()
            data = json.loads(original)
            self.assertEqual(data['audit_issues'], [])
            self.assertIs(data['inside_attack_trouble'], True)
            self.assertIn('Banging Heads', data['crossbones_subset']['omitted_powers'])
            with self.assertRaises((FileExistsError, ValueError)):
                run_demo(output)
            self.assertEqual(output.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
