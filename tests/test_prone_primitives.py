import unittest

from experimental.prone import ProneModifiers, attack_modifiers, stand


class PronePrimitiveTests(unittest.TestCase):
    def test_attacker_prone_troubles_melee_but_not_agility(self):
        self.assertEqual(attack_modifiers(attacker_prone=True, target_prone=False,
                                          ability='melee', attack_range='close'), ProneModifiers(0, 1))
        self.assertEqual(attack_modifiers(attacker_prone=True, target_prone=False,
                                          ability='agility', attack_range='ranged'), ProneModifiers(0, 0))

    def test_target_prone_affects_close_and_ranged_differently(self):
        self.assertEqual(attack_modifiers(attacker_prone=False, target_prone=True,
                                          ability='melee', attack_range='close'), ProneModifiers(1, 0))
        self.assertEqual(attack_modifiers(attacker_prone=False, target_prone=True,
                                          ability='agility', attack_range='ranged'), ProneModifiers(0, 1))

    def test_combined_effects_preserve_separate_sources(self):
        self.assertEqual(attack_modifiers(attacker_prone=True, target_prone=True,
                                          ability='melee', attack_range='close'), ProneModifiers(1, 1))
        self.assertEqual(attack_modifiers(attacker_prone=True, target_prone=True,
                                          ability='melee', attack_range='ranged'), ProneModifiers(0, 2))

    def test_standing_consumes_one_space(self):
        self.assertEqual(stand(prone=True, movement_remaining=5, can_move=True), (False, 4))
        self.assertEqual(stand(prone=True, movement_remaining=1, can_move=True), (False, 0))
        for kwargs in ({'prone': False, 'movement_remaining': 1, 'can_move': True},
                       {'prone': True, 'movement_remaining': 0, 'can_move': True},
                       {'prone': True, 'movement_remaining': 1, 'can_move': False},
                       {'prone': True, 'movement_remaining': True, 'can_move': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                stand(**kwargs)

    def test_rejects_invalid_attack_context(self):
        with self.assertRaises(ValueError):
            attack_modifiers(attacker_prone=1, target_prone=False, ability='melee', attack_range='close')
        with self.assertRaises(ValueError):
            attack_modifiers(attacker_prone=True, target_prone=False, ability='melee', attack_range='unknown')
