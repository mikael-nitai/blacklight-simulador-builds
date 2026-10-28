"""Integration and adversarial controls for experimental group sheet input."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from blacklight.engine import Profile
from combatants.duel_adapter import CURRENT_RULESET, compile_duel
from combatants.group import GroupBattle, GroupPolicy
from combatants.group_audit import audit_group_trace
from combatants.group_runner import GROUP_SCHEMA, run_group
from combatants.sheets import load_sheet, parse_sheet, sheet_record
from scripts.freeze_results import require_generic_provenance
from scripts import character_group


class TestGroupRunner(unittest.TestCase):
    def setUp(self):
        hero = load_sheet('characters/victor_halle/rank3_2026-10-27_split_fast.json')
        enemy = load_sheet('characters/examples/synthetic_rank4_split_fast.json')
        self.sheets = (hero, enemy, replace(enemy, name='Outro inimigo'))
        self.policies = (GroupPolicy('hero', weapon='hammer', offhand='blade',
                                     prefer_fast=True, split_targets=True, edge_mode='decline'),
                         GroupPolicy('enemy1'), GroupPolicy('enemy2'))
        self.teams = ('herois', 'inimigos', 'inimigos')
        self.roles = ('player', 'npc', 'npc')
        self.tie = (0, 1, 2)

    def run_group(self, sheets=None, policies=None, seed=0):
        return run_group(sheets or self.sheets, policies or self.policies,
                         teams=self.teams, initiative_roles=self.roles,
                         initiative_tie_order=self.tie, seed=seed, max_rounds=8)

    def test_full_trace_replays_and_keeps_explicit_experimental_scope(self):
        record = self.run_group()
        self.assertEqual(record, self.run_group())
        self.assertEqual(record['schema'], GROUP_SCHEMA)
        self.assertEqual(record['evidence_scope'], 'experimental_group_uncertified')
        self.assertEqual(record['audit_issues'], [])
        self.assertEqual(record['table_ruleset'], CURRENT_RULESET)
        self.assertTrue(all(item['build_legality'] == 'not_certified_by_this_mechanics_adapter'
                            for item in record['coverage']))
        self.assertEqual([item['name'] for item in record['sheets']],
                         [sheet.name for sheet in self.sheets])
        self.assertTrue(any(row['type'] == 'fast_use_start' and
                            len(set(row['targets'])) == 2 for row in record['result']['log']))

    def test_ruleset_and_unsupported_character_or_policy_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'current'):
            self.run_group(sheets=(replace(self.sheets[0], ruleset='unknown'), *self.sheets[1:]))
        with self.assertRaisesRegex(ValueError, 'weapon or action'):
            self.run_group(policies=(self.policies[0], GroupPolicy('invalid', weapon='blade'), self.policies[2]))
        modified = sheet_record(self.sheets[0])
        modified['abilities']['resilience'] = -1
        modified['defenses']['resilience'] = 9
        with self.assertRaisesRegex(ValueError, 'negative Resilience'):
            self.run_group(sheets=(parse_sheet(modified), *self.sheets[1:]))

    def test_experimental_record_cannot_pass_certified_freeze(self):
        with self.assertRaisesRegex(ValueError, 'Experimental group'):
            require_generic_provenance(self.run_group(), Path('.'), 'unused')

    def test_coordinated_fast_edge_forgery_is_rejected(self):
        record = self.run_group()
        # Both records are altered together: the earlier generic auditor did not
        # derive these two edges from the attacker's powers and traits.
        rows = deepcopy(record['result']['log'])
        check = next(row for row in rows if row['type'] == 'fast_limb_check' and row['edges'] == 2)
        attack = next(row for row in rows if row['type'] == 'attack' and row.get('trigger') == check['trigger'])
        check['edges'] = attack['edges'] = 0
        profiles = tuple(compile_duel(sheet) for sheet in self.sheets)
        battle = GroupBattle(profiles, self.policies, teams=self.teams, initiative_roles=self.roles,
                             initiative_tie_order=self.tie, seed=0, max_rounds=8, audit=True)
        result = battle.run()
        forged = replace(result, log=tuple(rows))
        self.assertTrue(any('pre-effect profile/state' in issue for issue in
                            audit_group_trace(forged, profiles, self.teams, seed=0, max_rounds=8)))

    def test_ally_target_and_fake_result_are_rejected(self):
        profiles = tuple(compile_duel(sheet) for sheet in self.sheets)
        battle = GroupBattle(profiles, self.policies, teams=self.teams, initiative_roles=self.roles,
                             initiative_tie_order=self.tie, seed=0, max_rounds=8, audit=True)
        result = battle.run()
        rows = deepcopy(list(result.log))
        declaration = next(row for row in rows if row['type'] == 'fast_use_start')
        declaration['targets'][0] = declaration['actor']
        forged = replace(result, log=tuple(rows), winner='fake')
        issues = audit_group_trace(forged, profiles, self.teams, seed=0, max_rounds=8)
        self.assertTrue(any('invalid or friendly Fast target' in issue for issue in issues))
        self.assertIn('group result winner/outcome mismatch', issues)

    def test_lowest_defense_uses_ranged_defense_and_brawling(self):
        shooter = Profile('Atirador', 3, 90, 90, 2, 4, 3, 1, 12, 14, 5, ranged_range=5)
        a = Profile('A', 3, 90, 90, 0, 6, 3, 1, 10, 16, 6)
        b = Profile('B', 3, 90, 90, 6, 0, 3, 1, 16, 10, 5)
        policy = GroupPolicy('shooter', target_order='lowest_defense')
        game = GroupBattle((shooter, a, b), (policy, policy, policy),
                           teams=('a', 'b', 'b'), seed=1)
        self.assertEqual(policy.choose_action(game.observe(0)).target_actor, 2)
        b = replace(b, powers=frozenset({'brawling'}))
        game = GroupBattle((shooter, a, b), (policy, policy, policy),
                           teams=('a', 'b', 'b'), seed=1)
        self.assertEqual(policy.choose_action(game.observe(0)).target_actor, 1)

    def test_cli_does_not_overwrite_or_publish_changed_sheet(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            config = json.loads(Path('examples/experimental_group_config.json').read_text(encoding='utf-8'))
            for index, row in enumerate(config['combatants']):
                original = (Path('examples') / row['sheet']).resolve()
                local = root / f'sheet-{index}.json'
                local.write_bytes(original.read_bytes())
                row['sheet'] = str(local)
            config_path = root / 'config.json'
            config_path.write_text(json.dumps(config), encoding='utf-8')
            output = root / 'run.json'
            with patch.object(sys, 'argv', ['character_group', str(config_path), '--output', str(output)]):
                character_group.main()
            first_bytes = output.read_bytes()
            self.assertEqual(json.loads(first_bytes)['evidence_scope'], 'experimental_group_uncertified')
            with patch.object(sys, 'argv', ['character_group', str(config_path), '--output', str(output)]):
                with self.assertRaises(FileExistsError):
                    character_group.main()
            self.assertEqual(output.read_bytes(), first_bytes)
            other = root / 'changed.json'
            real_run = character_group.run_group
            def mutate_input(*args, **kwargs):
                payload = real_run(*args, **kwargs)
                (root / 'sheet-0.json').write_text('{}', encoding='utf-8')
                return payload
            with patch.object(sys, 'argv', ['character_group', str(config_path), '--output', str(other)]), \
                    patch.object(character_group, 'run_group', side_effect=mutate_input):
                with self.assertRaisesRegex(RuntimeError, 'changed during execution'):
                    character_group.main()
            self.assertFalse(other.exists())


if __name__ == '__main__':
    unittest.main()
