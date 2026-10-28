"""Independent reference cases and invariants for Monte Carlo summaries."""

import unittest

from blacklight.experiment import (Moment, comparisons, independent_win_difference,
                                   scenarios, wilson)
from blacklight.sensitivity import difference


def row(wins, n):
    return {'n': n, 'win_rate': wins / n, 'outcomes': {'win': wins}}


class TestStatisticsFoundation(unittest.TestCase):
    def test_boundary_samples_keep_uncertainty(self):
        # Hand-calculated Newcombe/Wilson interval with alpha = 0.05/12.
        for wins in (0, 10):
            delta, lower, upper = independent_win_difference(
                row(wins, 10), row(wins, 10), alpha=0.05 / 12)
            self.assertEqual(delta, 0)
            self.assertAlmostEqual(lower, -0.450842623179003, places=12)
            self.assertAlmostEqual(upper, 0.450842623179003, places=12)

    def test_reference_difference_and_reversal_invariant(self):
        first, second = row(80, 100), row(40, 100)
        delta, lower, upper = independent_win_difference(first, second, alpha=0.05 / 12)
        self.assertAlmostEqual(delta, 0.4)
        self.assertAlmostEqual(lower, 0.203351396235868, places=12)
        self.assertAlmostEqual(upper, 0.555969859401599, places=12)
        reverse = independent_win_difference(second, first, alpha=0.05 / 12)
        self.assertAlmostEqual(reverse[0], -delta)
        self.assertAlmostEqual(reverse[1], -upper)
        self.assertAlmostEqual(reverse[2], -lower)

    def test_experiment_comparison_and_sensitivity_do_not_report_zero_width(self):
        rows = []
        for scenario in scenarios():
            for strategy in ('bare_attack', 'hammer'):
                rows.append({**row(10, 10), 'scenario': scenario.id, 'strategy': strategy})
        for comparison in comparisons(rows):
            lower, upper = comparison['simultaneous_ci_bonferroni']
            self.assertLess(lower, 0)
            self.assertGreater(upper, 0)
            self.assertIn('approximate', comparison['method'])
        lower, upper = difference(row(10, 10), row(10, 10))['ci95_independent']
        self.assertLess(lower, 0)
        self.assertGreater(upper, 0)

    def test_invalid_binomial_inputs_and_inconsistent_counts_are_rejected(self):
        for successes, n, alpha in ((-1, 10, 0.05), (11, 10, 0.05), (1, 0, 0.05),
                                    (True, 10, 0.05), (1, 10, 0), (1, 10, 1)):
            with self.subTest(successes=successes, n=n, alpha=alpha):
                with self.assertRaises(ValueError):
                    wilson(successes, n, alpha)
        inconsistent = {'n': 10, 'win_rate': 0.5, 'outcomes': {'win': 4}}
        with self.assertRaisesRegex(ValueError, 'disagrees'):
            independent_win_difference(inconsistent, row(1, 10))

    def test_one_observation_does_not_claim_zero_monte_carlo_error(self):
        moment = Moment()
        with self.assertRaises(ValueError):
            moment.summary()
        moment.add(1)
        self.assertEqual(moment.summary(), {'mean': 1.0, 'mc_se': None})
        moment.add(3)
        self.assertEqual(moment.summary(), {'mean': 2.0, 'mc_se': 1.0})


if __name__ == '__main__':
    unittest.main()
