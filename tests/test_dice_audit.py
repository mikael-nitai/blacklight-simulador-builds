"""Hand-constructed independent references for edge/trouble histories."""

import unittest

from blacklight.dice_audit import audit_rerolls


def entry(roll, traces):
    return {'seq': 1, 'roll': roll, 'rerolls': traces}


def trace(kind, index, original, rolled, kept):
    return {'kind': kind, 'index': index, 'original': original,
            'rolled': rolled, 'kept': kept}


class TestDiceAudit(unittest.TestCase):
    def test_marvel_one_is_better_than_a_six_for_edge(self):
        record = entry([6, 1, 4], [trace('edge', 1, 6, 1, 1)])
        self.assertEqual(audit_rerolls(record, edges=1, troubles=0), [])
        forged = entry([6, 6, 4], [trace('edge', 1, 6, 1, 6)])
        self.assertTrue(any('impossible' in issue
                            for issue in audit_rerolls(forged, edges=1, troubles=0)))

    def test_trouble_must_choose_strongest_die_and_keep_worse(self):
        valid = entry([3, 4, 2], [trace('trouble', 0, 6, 3, 3)])
        self.assertEqual(audit_rerolls(valid, edges=0, troubles=1), [])
        wrong_die = entry([6, 3, 2], [trace('trouble', 1, 4, 3, 3)])
        self.assertTrue(any('strongest' in issue
                            for issue in audit_rerolls(wrong_die, edges=0, troubles=1)))

    def test_trouble_treats_marvel_one_as_stronger_than_other_six(self):
        valid = entry([5, 5, 6], [trace('trouble', 1, 1, 5, 5)])
        self.assertEqual(audit_rerolls(valid, edges=0, troubles=1), [])
        wrong = entry([5, 1, 5], [trace('trouble', 2, 6, 5, 5)])
        self.assertTrue(any('strongest' in issue
                            for issue in audit_rerolls(wrong, edges=0, troubles=1)))

    def test_ultimate_fantastic_ignores_trouble_but_other_rolls_do_not(self):
        self.assertEqual(audit_rerolls(entry([6, 1, 6], []), edges=0, troubles=2), [])
        self.assertTrue(any('all troubles' in issue for issue in
                            audit_rerolls(entry([6, 6, 6], []), edges=0, troubles=1)))

    def test_edges_can_be_declined_but_cannot_exceed_allowance(self):
        self.assertEqual(audit_rerolls(entry([2, 3, 4], []), edges=2, troubles=0), [])
        two = entry([4, 3, 4], [trace('edge', 0, 1, 2, 2),
                                 trace('edge', 0, 2, 4, 4)])
        self.assertEqual(audit_rerolls(two, edges=2, troubles=0), [])
        self.assertTrue(any('available edges' in issue
                            for issue in audit_rerolls(two, edges=1, troubles=0)))
        self.assertTrue(any('cancel' in issue
                            for issue in audit_rerolls(two, edges=1, troubles=1)))

    def test_broken_chain_and_invalid_face_are_rejected(self):
        broken = entry([4, 3, 4], [trace('edge', 0, 1, 2, 2),
                                    trace('edge', 0, 3, 4, 4)])
        self.assertTrue(any('chain' in issue
                            for issue in audit_rerolls(broken, edges=2, troubles=0)))
        invalid = entry([7, 3, 4], [])
        self.assertTrue(audit_rerolls(invalid, edges=0, troubles=0))


if __name__ == '__main__':
    unittest.main()
