"""Compatibility labels must stay conservative when evidence is absent."""

import unittest

from scripts.result_compatibility import (PRE_SPLIT_FAST_COMMITS, classify_ruleset,
                                          zero_width_intervals)


class TestResultCompatibility(unittest.TestCase):
    def test_explicit_versions_and_unknowns_are_not_confused(self):
        old_commit = next(iter(PRE_SPLIT_FAST_COMMITS))
        self.assertEqual(classify_ruleset({'table_ruleset': 'split_fast_v3'}, 'new'),
                         'current_ruleset_declared')
        self.assertEqual(classify_ruleset({'table_ruleset': 'split_fast_v3'}, old_commit),
                         'conflicting_ruleset_and_snapshot')
        self.assertEqual(classify_ruleset({'table_ruleset': 'literal_marvel_pool_v2'}, 'new'),
                         'historical_ruleset_declared')
        self.assertEqual(classify_ruleset({}, old_commit), 'historical_snapshot_pre_split_fast')
        self.assertEqual(classify_ruleset({}, 'unknown'), 'unknown_ruleset')
        self.assertEqual(classify_ruleset({'table_ruleset': 'unrecognized'}, old_commit),
                         'unknown_ruleset')
        self.assertEqual(classify_ruleset({'table_ruleset': 'split_fast_v3',
                                           'policy_provenance': 'external_unverified'}, 'new'),
                         'experimental_policy_unverified')

    def test_known_zero_width_interval_fields_are_counted_once(self):
        payload = {'comparisons': [{'simultaneous_ci_bonferroni': [0, 0]},
                                   {'simultaneous_ci_bonferroni': [-0.1, 0.1]}],
                   'pairs': [{'ci95_independent': [1, 1]}],
                   'unrelated': [0, 0]}
        self.assertEqual(zero_width_intervals(payload), 2)


if __name__ == '__main__':
    unittest.main()
