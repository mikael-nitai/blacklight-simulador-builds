"""Independent small examples for the preregistered exploratory selector."""

from copy import deepcopy
import unittest

from scripts.current_study_dev import POLICIES, SCENARIOS
from scripts.current_study_select import select_candidates


class TestCurrentStudySelector(unittest.TestCase):
    def test_worst_cell_then_sum_then_lexical_id(self):
        counts = {scenario: dict.fromkeys(POLICIES, 100) for scenario in SCENARIOS}
        counts['mirror']['bare'] = 999  # control is never eligible for the two slots
        counts['mirror']['hammer'] = 200
        counts['rank4']['hammer'] = 300
        counts['gunner_corridor']['hammer'] = 200
        counts['mirror']['hammer_fast_hammer'] = 200
        counts['rank4']['hammer_fast_hammer'] = 300
        counts['gunner_corridor']['hammer_fast_hammer'] = 200
        counts['mirror']['blade_fast_blade'] = 201
        counts['rank4']['blade_fast_blade'] = 201
        counts['gunner_corridor']['blade_fast_blade'] = 201
        self.assertEqual(select_candidates(counts), ('blade_fast_blade', 'hammer'))

    def test_incomplete_or_noninteger_data_cannot_select(self):
        counts = {scenario: dict.fromkeys(POLICIES, 0) for scenario in SCENARIOS}
        for bad in ('missing_scenario', 'missing_candidate', 'boolean', 'above_n'):
            matrix = deepcopy(counts)
            if bad == 'missing_scenario':
                matrix.pop('mirror')
            elif bad == 'missing_candidate':
                matrix['mirror'].pop('bare')
            elif bad == 'boolean':
                matrix['mirror']['hammer'] = True
            else:
                matrix['mirror']['hammer'] = 1001
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                select_candidates(matrix)
