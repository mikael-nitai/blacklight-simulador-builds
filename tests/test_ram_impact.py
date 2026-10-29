import unittest

from experimental.ram_impact import RamImpact, ram_impact


class RamImpactTests(unittest.TestCase):
    def arguments(self):
        return dict(success=True, fantastic_success=False, full_dice=6, ability=6,
                    target_reduction=2, attacker_reduction=1,
                    target_faces=(1, 2, 3, 4, 5, 6), self_pool='shared')

    def test_normal_success_reduces_each_recipient_before_multiplying(self):
        self.assertEqual(ram_impact(**self.arguments()), RamImpact(21, 26, 42, 26, False))

    def test_fantastic_triples_target_regular_not_self_damage(self):
        args = self.arguments()
        args['fantastic_success'] = True
        self.assertEqual(ram_impact(**args), RamImpact(21, 26, 63, 26, True))

    def test_separate_pool_is_a_distinct_explicit_hypothesis(self):
        args = self.arguments()
        args.update(self_pool='separate', attacker_faces=(6, 6, 6, 6, 6, 6))
        self.assertEqual(ram_impact(**args), RamImpact(21, 36, 42, 36, False))

    def test_full_damage_reduction_blocks_regular_damage_even_with_ability(self):
        args = self.arguments()
        args.update(target_reduction=6, attacker_reduction=9)
        self.assertEqual(ram_impact(**args), RamImpact(0, 0, 0, 0, False))

    def test_miss_spends_no_damage_dice_or_prone(self):
        args = self.arguments()
        args.update(success=False, target_faces=())
        self.assertEqual(ram_impact(**args), RamImpact(0, 0, 0, 0, False))
        args.update(self_pool='separate', attacker_faces=())
        self.assertEqual(ram_impact(**args), RamImpact(0, 0, 0, 0, False))

    def test_rejects_ambiguous_or_impossible_inputs(self):
        for changes in ({'self_pool': 'unknown'}, {'self_pool': 'separate'},
                        {'attacker_faces': (1, 2, 3, 4, 5, 6)},
                        {'success': False, 'fantastic_success': True},
                        {'target_faces': (1, 2, 3, 4, 5, 7)},
                        {'target_reduction': True}, {'full_dice': -1}):
            args = self.arguments()
            args.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                ram_impact(**args)
