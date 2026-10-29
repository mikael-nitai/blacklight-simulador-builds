from copy import deepcopy
import json
from pathlib import Path
import unittest

from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.sheets import load_sheet
from experimental.crossbones_subset import build_crossbones_subset
from experimental.ranged_powers_duel import RangedPowersPolicy
from experimental.smg_audit import audit_submachine_duel
from experimental.smg_duel import SubmachineDuel

ROOT = Path(__file__).resolve().parents[1]


def evidence():
    return json.loads((ROOT / 'character_evidence/crossbones_core_p155.json').read_text(encoding='utf-8'))


class CrossbonesSubsetTests(unittest.TestCase):
    def test_subset_preserves_numbers_and_exposes_omitted_features(self):
        subset = build_crossbones_subset(evidence(), accept_incomplete=True)
        p = subset.profile
        self.assertEqual((p.rank, p.max_health, p.max_focus, p.melee, p.agility,
                          p.resilience, p.vigilance, p.logic, p.melee_defense,
                          p.agility_defense, p.run_speed, p.initiative_modifier),
                         (3, 90, 90, 4, 5, 3, 2, 1, 14, 15, 6, 2))
        self.assertEqual((p.ranged_range, p.ranged_bonus, p.ranged_is_ammunition), (10, 2, True))
        self.assertEqual(subset.ranged_weapon, 'submachine_gun')
        self.assertIn('Slow-Motion Dodge', subset.included_powers)
        self.assertIn('Fast Hands', subset.omitted_powers)
        self.assertIn('Point-Blank Parry', subset.omitted_powers)
        self.assertIn('Bloodthirsty', subset.omitted_traits)
        self.assertIn('Villainous', subset.omitted_tags)

    def test_explicit_consent_and_source_requirements(self):
        with self.assertRaises(ValueError):
            build_crossbones_subset(evidence(), accept_incomplete=False)
        for mutator in (lambda d: d['powers']['Basic'].remove('Accuracy 2'),
                        lambda d: d['weapon_reference'].__setitem__('range_spaces', 6),
                        lambda d: d.__setitem__('health_damage_reduction_printed', '?'),
                        lambda d: d['powers']['Ranged Weapons'].remove('Fast Hands'),
                        lambda d: d['abilities']['agility'].__setitem__('score', 6),
                        lambda d: d['source'].__setitem__('sha256', 'wrong')):
            data = deepcopy(evidence())
            mutator(data)
            with self.assertRaises(ValueError):
                build_crossbones_subset(data, accept_incomplete=True)

    def test_audited_subset_against_current_victor(self):
        subset = build_crossbones_subset(evidence(), accept_incomplete=True)
        victor = compile_duel(load_sheet(ROOT / 'characters/victor_halle/rank3_2026-10-27_split_fast.json'))
        profiles = (subset.profile, victor)
        policies = (RangedPowersPolicy('crossbones parcial', use_ram=False),
                    RangedPowersPolicy('victor', weapon='hammer', offhand='blade',
                                       prefer_fast=True, effect_limb=1, use_ram=False))
        args = dict(seed=30, initial_prone=(False, False), initial_distance=2, max_rounds=6,
                    audit=True, action_registry=DEFAULT_ACTIONS,
                    ranged_weapons=(subset.ranged_weapon, 'generic'))
        result = SubmachineDuel(profiles, policies, **args).run()
        self.assertEqual(result, SubmachineDuel(profiles, policies, **args).run())
        self.assertEqual(audit_submachine_duel(result, profiles, initial_prone=(False, False),
                         initial_distance=2, expected_seed=30, max_rounds=6,
                         ranged_weapons=(subset.ranged_weapon, 'generic'),
                         ruleset=SubmachineDuel.table_ruleset), [])
        self.assertTrue(any(event['type'] == 'double_tap_end' and event['bleeding']
                            for event in result.log))
        self.assertTrue(any(event['type'] == 'smg_close_check' for event in result.log))
        self.assertTrue(any(event['type'] == 'fast_use_start' and event['actor'] == 'Blacklight'
                            for event in result.log))
