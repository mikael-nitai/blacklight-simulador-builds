from copy import deepcopy
from dataclasses import replace
import unittest

from blacklight.engine import Action
from experimental.ranged_powers_duel import RangedPowersDuel
from experimental.smg_audit import audit_submachine_duel
from experimental.smg_duel import SubmachineDuel
from tests.test_double_tap_duel import FixedDice
from tests.test_ranged_powers_duel import fixture


class SubmachineDuelTests(unittest.TestCase):
    def test_close_boundary_adds_trouble_without_stacking_damage_bonus(self):
        profiles, policies, args = fixture()
        for distance, expected in ((5, 2), (6, 1)):
            args['initial_distance'] = distance
            duel = SubmachineDuel(profiles, policies, ranged_weapons=('submachine_gun', 'generic'), **args)
            duel.round = 1
            duel._reset_reactions_for_round()
            duel.active_actor = 0
            duel.fighters[0].standard_available = True
            duel.rng = FixedDice((6, 6, 6, 6, 6))
            duel.damage_rng = FixedDice((3,) * 20)
            duel._act(0, Action('ranged'))
            attack = next(e for e in duel.log if e['type'] == 'attack')
            self.assertEqual(attack['troubles'], expected)  # includes Slow-Motion Dodge
            self.assertEqual(attack['damage_components'][0]['full_multiplier'], 5)
            self.assertEqual(attack['calculated_damage'], 20)

    def test_double_tap_and_slow_dodge_are_audited_with_submachine(self):
        profiles, policies, args = fixture(prone=True)
        observed = set()
        for seed in range(35):
            args['seed'] = seed
            duel = SubmachineDuel(profiles, policies, ranged_weapons=('submachine_gun', 'generic'), **args)
            result = duel.run()
            self.assertEqual(audit_submachine_duel(result, profiles,
                ranged_weapons=('submachine_gun', 'generic'), initial_prone=args['initial_prone'],
                initial_distance=1, expected_seed=seed, max_rounds=4, ruleset=duel.table_ruleset), [])
            for event in result.log:
                if event['type'] == 'attack' and event['actor'] == 'Atirador' and event['troubles'] == 3:
                    observed.add('all_three_troubles')
                if event['type'] in ('double_tap_end', 'slow_motion_dodge', 'smg_close_check'):
                    observed.add(event['type'])
        self.assertEqual(observed, {'all_three_troubles', 'double_tap_end',
                                    'slow_motion_dodge', 'smg_close_check'})

    def test_generic_equipment_replays_existing_host(self):
        profiles, policies, args = fixture()
        for seed in range(15):
            args['seed'] = seed
            self.assertEqual(SubmachineDuel(profiles, policies, ranged_weapons=('generic', 'generic'), **args).run(),
                             RangedPowersDuel(profiles, policies, **args).run())

    def test_invalid_weapon_profiles_are_rejected(self):
        profiles, policies, args = fixture()
        for bad in (replace(profiles[0], ranged_range=6),
                    replace(profiles[0], ranged_is_ammunition=False),
                    replace(profiles[0], ranged_bonus=0)):
            with self.assertRaises(ValueError):
                SubmachineDuel((bad, profiles[1]), policies,
                               ranged_weapons=('submachine_gun', 'generic'), **args)

    def test_audit_rejects_missing_or_forged_close_check(self):
        profiles, policies, args = fixture()
        duel = SubmachineDuel(profiles, policies, ranged_weapons=('submachine_gun', 'generic'), **args)
        result = duel.run()
        context = dict(ranged_weapons=('submachine_gun', 'generic'), initial_prone=(False, False),
                       initial_distance=1, expected_seed=1, max_rounds=4, ruleset=duel.table_ruleset)
        self.assertEqual(audit_submachine_duel(result, profiles, **context), [])
        index = next(i for i, e in enumerate(result.log) if e['type'] == 'smg_close_check')
        for field, value in (('distance', 6), ('added_troubles', 2), ('trigger', 999)):
            log = deepcopy(result.log)
            log[index][field] = value
            self.assertTrue(audit_submachine_duel(replace(result, log=log), profiles, **context))
        log = list(deepcopy(result.log))
        log.pop(index)
        for seq, event in enumerate(log, 1):
            event['seq'] = seq
        self.assertTrue(audit_submachine_duel(replace(result, log=tuple(log)), profiles, **context))
