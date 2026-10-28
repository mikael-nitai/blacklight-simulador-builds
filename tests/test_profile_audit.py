"""A coherent attack ledger must still agree with the declared fighters."""

from copy import deepcopy
from dataclasses import replace
import unittest

from blacklight.audit import audit_log, audit_profiled_log
from blacklight.engine import Action, Duel, Profile, blacklight_profile
from blacklight.policies import HAMMER


class TestProfileAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        hero = blacklight_profile()
        opponent = replace(hero, name='Opponent')
        cls.profiles = (hero, opponent)
        cls.log = Duel(cls.profiles, (HAMMER, HAMMER), seed=2,
                       audit=True).run().log
        cls.health = {p.name: p.max_health for p in cls.profiles}
        cls.focus = {p.name: p.max_focus for p in cls.profiles}

    def check_forgery(self, change, expected):
        log = deepcopy(self.log)
        change(log)
        # This is deliberately self-consistent according to the old ledger
        # alone: the independent sheet check is what must reject it.
        self.assertEqual(audit_log(log, self.health, self.focus), [])
        issues = audit_profiled_log(log, self.profiles)
        self.assertTrue(any(expected in issue for issue in issues), issues)

    def test_real_control_follows_declared_profiles(self):
        self.assertEqual(audit_profiled_log(self.log, self.profiles), [])

    def test_extra_to_hit_bonus_and_adjusted_total_are_rejected(self):
        def change(log):
            event = next(e for e in log if e['type'] == 'attack' and e['success'])
            event['check_modifier'] += 7
            event['total'] += 7
        self.check_forgery(change, 'profile attack modifier')

    def test_easier_defense_with_unchanged_result_is_rejected(self):
        def change(log):
            event = next(e for e in log if e['type'] == 'attack' and e['success'])
            event['target_number'] -= 1
        self.check_forgery(change, 'profile target defense')

    def test_fabricated_rank_and_bonus_on_miss_are_rejected(self):
        for field, expected in (('rank', 'profile rank'),
                                ('bonus_candidates', 'profile weapon bonus'),
                                ('ability_for_damage', 'profile damage ability'),
                                ('reduction', 'profile reduction')):
            def change(log, field=field):
                event = next(e for e in log if e['type'] == 'attack' and not e['success'])
                if field == 'bonus_candidates':
                    event[field] = [99]
                else:
                    event[field] += 1
            with self.subTest(field=field):
                self.check_forgery(change, expected)

    def test_forged_initiative_modifier_and_total_are_rejected(self):
        def change(log):
            event = next(e for e in log if e['type'] == 'initiative')
            event['modifier'] += 7
            event['total'] += 7
        self.check_forgery(change, 'profile initiative modifier')

    def test_forged_rerolls_are_rejected_even_if_final_roll_is_unchanged(self):
        for kind in ('initiative', 'attack'):
            def change(log, kind=kind):
                event = next(e for e in log if e['type'] == kind and e.get('rerolls'))
                trace = event['rerolls'][0]
                # Both the first and second die show the same face, so keeping
                # a different face is impossible despite a plausible final roll.
                false_face = 2 if trace['kept'] != 2 else 3
                trace['original'] = trace['rolled'] = false_face
            with self.subTest(kind=kind):
                log = deepcopy(self.log)
                change(log)
                issues = audit_profiled_log(log, self.profiles)
                self.assertTrue(any('reroll' in issue for issue in issues), issues)

    def test_attack_by_a_fighter_without_the_weapon_is_rejected(self):
        changed = tuple(replace(p, weapons=p.weapons - {'hammer'}) for p in self.profiles)
        self.assertEqual(audit_log(self.log, self.health, self.focus), [])
        self.assertTrue(any('profile capabilities' in issue
                            for issue in audit_profiled_log(self.log, changed)))

    def test_coherent_falsified_hit_is_checked_against_fighter_and_target(self):
        class FixedDice:
            def __init__(self, faces):
                self.faces = iter(faces)

            def randint(self, low, high):
                return next(self.faces)

        hero = replace(blacklight_profile(), heroic=False)
        foe = Profile('Target', 3, 1000, 90, 4, 2, 3, 2, 14, 12, 5)
        policies = (replace(HAMMER, edge_mode='decline', riposte=False), HAMMER)
        battle = Duel((hero, foe), policies, seed=3, audit=True)
        battle.round, battle.active_actor = 1, 0
        battle.fighters[0].standard_available = True
        battle._act(0, Action('stance'))
        battle.round = 2
        battle.fighters[0].standard_available = True
        battle.rng = FixedDice([6, 6, 6])
        battle.damage_rng = FixedDice([1] * 20)
        battle._act(0, Action('hammer'))
        original = battle.log
        attack = next(e for e in original if e['type'] == 'attack')
        # Hand reference: Rank 3 + Mighty 3 + hammer 2 = 8 dice, each 1
        # counts as 6, plus Melee 6 doubled by Attack Stance = 60.
        self.assertEqual((attack['ability_for_damage'], attack['calculated_damage']), (12, 60))
        profiles = (hero, foe)
        health = {p.name: p.max_health for p in profiles}
        focus = {p.name: p.max_focus for p in profiles}
        self.assertEqual(audit_profiled_log(original, profiles), [])

        for field, expected in (('rank', 'profile rank'),
                                ('bonus', 'profile weapon bonus'),
                                ('ability', 'profile damage ability'),
                                ('reduction', 'profile reduction'),
                                ('applied', 'applied damage')):
            forged = deepcopy(original)
            row = next(e for e in forged if e['type'] == 'attack')
            component = row['damage_components'][0]
            delta = 0
            if field in ('rank', 'bonus'):
                if field == 'rank':
                    row['rank'] += 1
                else:
                    row['bonus_candidates'] = [value + 1 for value in row['bonus_candidates']]
                    component['bonus_candidates'] = [value + 1 for value in component['bonus_candidates']]
                component['full_multiplier'] += 1
                component['dice_after_reduction'] += 1
                component['dice_rolled'] += 1
                component['faces'].append(1)
                component['damage_without_reduction'] += 6
                delta = 6
            elif field == 'ability':
                row['ability_for_damage'] += 2
                component['ability_added'] += 2
                component['damage_without_reduction'] += 2
                delta = 2
            elif field == 'reduction':
                row['reduction'] += 1
                component['reduction'] += 1
                component['dice_after_reduction'] -= 1
                component['dice_rolled'] -= 1
                component['counterfactual_faces'].append(component['faces'].pop())
                delta = -6
            else:
                # The old ledger allowed applying less than calculated damage.
                row['damage'] -= 1
                row['health_after'] += 1
            if field != 'applied':
                component['damage'] += delta
                row['calculated_damage'] += delta
                row['damage'] += delta
                row['health_after'] -= delta
            with self.subTest(field=field):
                self.assertEqual(audit_log(forged, health, focus), [])
                issues = audit_profiled_log(forged, profiles)
                self.assertTrue(any(expected in issue for issue in issues), issues)


if __name__ == '__main__':
    unittest.main()
