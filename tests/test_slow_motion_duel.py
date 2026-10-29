import unittest
from dataclasses import replace
from copy import deepcopy

from blacklight.audit import audit_profiled_log
from blacklight.engine import Profile
from blacklight.result_audit import audit_battle_result
from blacklight.rulesets import CURRENT_RULESET
from experimental.slow_motion_duel import SlowMotionDuel, SlowMotionPolicy
from experimental.slow_motion_audit import audit_slow_motion_duel


def profile(name, *, powers=frozenset(), ranged_range=0):
    return Profile(name, 3, 90, 90, 3, 3, 3, 1, 13, 13, 5,
                   powers=powers, ranged_range=ranged_range, heroic=True)


class SlowMotionDuelTests(unittest.TestCase):
    def battle(self, *, powers=frozenset({'slow_motion_dodge'}), choose=True):
        profiles = (profile('Shooter', ranged_range=5), profile('Defender', powers=powers))
        policies = (SlowMotionPolicy('shoot'), SlowMotionPolicy('defend', dodge_agility_attacks=choose))
        duel = SlowMotionDuel(profiles, policies, seed=10, initial_distance=2, audit=True)
        duel.round = 1
        duel._reset_reactions_for_round()
        return duel

    def test_reaction_is_recorded_before_roll_and_adds_trouble(self):
        duel = self.battle()
        duel._attack(0, 'ranged')
        spent, dodge, attack = [e for e in duel.log if e['type'] in
                                ('reaction_spent', 'slow_motion_dodge', 'attack')]
        self.assertEqual((spent['trigger'], dodge['trigger'], attack['trigger']), (1, 1, 1))
        self.assertLess(dodge['seq'], attack['seq'])
        self.assertEqual((spent['remaining'], attack['troubles']), (0, 1))
        self.assertEqual([r['kind'] for r in attack['rerolls']], ['trouble'])

    def test_brawling_redirects_the_attack_to_melee_so_no_dodge(self):
        duel = self.battle(powers=frozenset({'slow_motion_dodge', 'brawling'}))
        duel._attack(0, 'ranged')
        self.assertFalse(any(e['type'] == 'slow_motion_dodge' for e in duel.log))
        self.assertEqual(duel.fighters[1].reactions, 1)
        self.assertEqual(next(e for e in duel.log if e['type'] == 'attack')['troubles'], 0)

    def test_declined_and_exhausted_reaction_do_not_add_trouble(self):
        for choose, remaining in ((False, 1), (True, 0)):
            with self.subTest(choose=choose, remaining=remaining):
                duel = self.battle(choose=choose)
                duel.fighters[1].reactions = remaining
                duel._attack(0, 'ranged')
                attack = next(e for e in duel.log if e['type'] == 'attack')
                self.assertEqual(attack['troubles'], 0)
                self.assertEqual(duel.fighters[1].reactions, remaining)

    def test_long_range_and_existing_dodge_each_add_trouble(self):
        duel = self.battle()
        duel.distance = 6
        duel.fighters[1].dodging = True
        duel._attack(0, 'ranged')
        attack = next(e for e in duel.log if e['type'] == 'attack')
        self.assertEqual(attack['troubles'], 3)
        self.assertEqual(len(attack['rerolls']), 3)

    def test_full_duel_baseline_audits_and_deterministic_replay(self):
        profiles = (profile('Shooter', ranged_range=5),
                    profile('Defender', powers=frozenset({'slow_motion_dodge'})))
        policies = (SlowMotionPolicy('shoot'), SlowMotionPolicy('defend'))
        def run(seed):
            return SlowMotionDuel(profiles, policies, seed=seed, initial_distance=2,
                                  max_rounds=8, audit=True).run()
        for seed in range(10):
            result = run(seed)
            self.assertEqual(result, run(seed))
            self.assertEqual(audit_profiled_log(result.log, profiles, ruleset=CURRENT_RULESET), [])
            self.assertEqual(audit_battle_result(result, profiles, expected_seed=seed, max_rounds=8), [])
            self.assertEqual(audit_slow_motion_duel(result, profiles, seed=seed, max_rounds=8,
                                                    initial_distance=2), [])

    def test_independent_audit_rejects_forged_reaction_and_trouble(self):
        profiles = (profile('Shooter', ranged_range=5),
                    profile('Defender', powers=frozenset({'slow_motion_dodge'})))
        policies = (SlowMotionPolicy('shoot'), SlowMotionPolicy('defend'))
        result = SlowMotionDuel(profiles, policies, seed=10, initial_distance=2,
                                max_rounds=8, audit=True).run()
        event_index = next(i for i, e in enumerate(result.log) if e['type'] == 'slow_motion_dodge')
        for field, value in (('before_roll', False), ('trigger', 999), ('added_troubles', 2)):
            log = deepcopy(result.log)
            log[event_index][field] = value
            forged = replace(result, log=log)
            self.assertTrue(audit_slow_motion_duel(forged, profiles, seed=10, max_rounds=8,
                                                   initial_distance=2))

    def test_unsupported_combinations_are_rejected(self):
        duel = self.battle()
        profiles = tuple(f.profile for f in duel.fighters)
        policies = tuple(duel.policies)
        for bad in (replace(profiles[0], heroic=False),
                    replace(profiles[0], powers=frozenset({'fast_strikes'})),
                    replace(profiles[0], weapons=frozenset({'blade'}))):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                SlowMotionDuel((bad, profiles[1]), policies, seed=1, audit=True)


if __name__ == '__main__':
    unittest.main()
