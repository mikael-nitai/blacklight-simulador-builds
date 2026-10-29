import unittest

from scripts.current_study_analysis import ALPHA, PAIRS, compare


def row(wins, n=10000):
    return {'n': n, 'win_rate': wins / n, 'outcomes': {'win': wins}}


class ConfirmationAnalysisTests(unittest.TestCase):
    def test_family_and_adjustment_are_preregistered(self):
        self.assertEqual(len(PAIRS), 5)
        self.assertEqual(ALPHA, 0.05 / 15)
        self.assertEqual(PAIRS[-1], ('hammer_fast_hammer', 'hammer_fast_blade'))

    def test_large_difference_and_direction(self):
        higher = compare(row(8000), row(4000))
        lower = compare(row(4000), row(8000))
        self.assertEqual(higher['conclusion'], 'first_higher')
        self.assertEqual(lower['conclusion'], 'second_higher')
        self.assertAlmostEqual(higher['difference'], -lower['difference'])

    def test_saturated_rates_remain_inconclusive(self):
        result = compare(row(10000), row(10000))
        self.assertEqual(result['conclusion'], 'inconclusive')
        self.assertLess(result['conservative_interval'][0], 0)
        self.assertGreater(result['conservative_interval'][1], 0)

    def test_mismatched_counts_are_rejected(self):
        with self.assertRaises(ValueError):
            compare({'n': 100, 'win_rate': 0.9, 'outcomes': {'win': 1}}, row(1))
