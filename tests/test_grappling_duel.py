from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.sheets import load_sheet
from experimental.crossbones_grapple_subset import build_crossbones_grapple_subset
from experimental.grappling_duel import GrapplingDuel, GrapplingPolicy
from experimental.grappling_duel_audit import audit_grappling_duel
from scripts.crossbones_ram_demo import EVIDENCE, VICTOR
from scripts.crossbones_grapple_demo import run as run_demo


class GrapplingDuelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subset = build_crossbones_grapple_subset(json.loads(EVIDENCE.read_text(encoding='utf-8')),
                                                  accept_incomplete=True)
        cls.profiles = (subset.profile, compile_duel(load_sheet(VICTOR)))
        cls.weapons = (subset.ranged_weapon, 'generic')
        cls.policies = (GrapplingPolicy('crossbones', prefer_grapple=True, prefer_stopping=True,
                          use_ram=False, treat_bleeding=True, kite=True, move_after_attack=True),
                        GrapplingPolicy('victor', weapon='hammer', shield_react=True,
                                        use_ram=False, escape_reaction=True))
        assert 'Grappling Technique' in subset.included_powers and 'Banging Heads' in subset.omitted_powers

    def run_case(self, seed, mode='attack'):
        duel = GrapplingDuel(self.profiles, self.policies, seed=seed, initial_prone=(False, False),
            initial_distance=1, max_rounds=4, audit=True, action_registry=DEFAULT_ACTIONS,
            ranged_weapons=self.weapons, stop_on_attacker=self.profiles[1].name,
            declared_armed_lethal=(self.profiles[0].name,), escape_trigger_mode=mode)
        return duel, duel.run()

    def audit_case(self, result, seed, mode='attack'):
        return audit_grappling_duel(result, self.profiles, declared_armed_lethal=(self.profiles[0].name,),
            escape_trigger_mode=mode, ranged_weapons=self.weapons, initial_prone=(False, False),
            initial_distance=1, expected_seed=seed, max_rounds=4, ruleset='split_fast_v3',
            self_damage_mode='stop_before_heal_reject_lethal', stop_on_attacker=self.profiles[1].name)

    def test_50_seed_duels_replay_and_pass_auditors_in_both_trigger_variants(self):
        seen = set()
        cases = set()
        for mode in ('attack', 'condition'):
            for seed in range(50):
                with self.subTest(seed=seed, mode=mode):
                    _, result = self.run_case(seed, mode)
                    self.assertEqual(result, self.run_case(seed, mode)[1])
                    self.assertEqual(self.audit_case(result, seed, mode), [])
                    seen.update(e['type'] for e in result.log
                                if e['type'] in ('grapple_start', 'grapple_end', 'grapple_escape'))
                    for event in result.log:
                        if event['type'] == 'grapple_end':
                            tx = event['transaction']
                            cases.add('miss' if not tx['attack_success'] else
                                      'fantastic' if tx['fantastic_success'] else 'hit')
                            if tx['attack_success'] and tx['applied_damage'] == 0:
                                cases.add('zero_damage_hit')
                        elif event['type'] == 'grapple_escape':
                            cases.add(event['timing'])
                            if event['transaction']['before']['pinned']:
                                cases.add('pinned_escape')
        self.assertEqual(seen, {'grapple_start', 'grapple_end', 'grapple_escape'})
        self.assertTrue({'miss', 'hit', 'fantastic', 'zero_damage_hit', 'standard', 'reaction',
                         'pinned_escape'}.issubset(cases))

    def test_shield_then_condition_trigger_reaction_and_attack_trigger_suppression(self):
        witnessed = False
        for seed in range(50):
            _, result = self.run_case(seed, 'condition')
            for i, event in enumerate(result.log):
                if event['type'] != 'grapple_end' or not event['transaction']['attack_success']:
                    continue
                trigger = event['trigger']
                shield = any(e['type'] == 'shield_activate' and e.get('trigger') == trigger
                             for e in result.log[:i])
                following = result.log[i + 1:i + 3]
                if shield and len(following) == 2 and following[0].get('source') == 'grapple_escape':
                    witnessed = True
                    self.assertEqual(following[0]['trigger'], trigger + 1)
                    self.assertEqual(following[1]['type'], 'grapple_escape')
                    self.assertEqual(self.audit_case(result, seed, 'condition'), [])
                    rows = deepcopy(list(result.log))
                    rows[i + 1]['trigger'] = trigger
                    self.assertTrue(self.audit_case(replace(result, log=tuple(rows)), seed, 'condition'))
                    break
            if witnessed:
                break
        self.assertTrue(witnessed)

    def test_auditor_rejects_tampered_cost_condition_and_escape(self):
        _, result = self.run_case(5)
        cost = next(i for i, e in enumerate(result.log) if e.get('source') == 'grappling_technique')
        end = next(i for i, e in enumerate(result.log) if e['type'] == 'grapple_end')
        esc = next(i for i, e in enumerate(result.log) if e['type'] == 'grapple_escape')
        for index, field, value in ((cost, 'amount', 4), (end, 'trigger', 999)):
            rows = deepcopy(list(result.log)); rows[index][field] = value
            self.assertTrue(self.audit_case(replace(result, log=tuple(rows)), 5))
        rows = deepcopy(list(result.log)); rows[esc]['transaction']['total'] += 1
        self.assertTrue(self.audit_case(replace(result, log=tuple(rows)), 5))

    def test_demo_is_audited_and_never_overwrites(self):
        with TemporaryDirectory() as directory, patch('scripts.crossbones_grapple_demo.source_commit', return_value='test'):
            output = Path(directory) / 'demo.json'
            run_demo(output)
            original = output.read_bytes()
            data = json.loads(original)
            self.assertEqual(data['audit_issues'], [])
            self.assertIn('Grappling Technique', data['crossbones_subset']['included_powers'])
            self.assertIn('Banging Heads', data['crossbones_subset']['omitted_powers'])
            with self.assertRaises((FileExistsError, ValueError)):
                run_demo(output)
            self.assertEqual(output.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
