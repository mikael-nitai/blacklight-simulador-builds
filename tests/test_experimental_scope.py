"""Experimental replay outputs identify their limited evidence scope."""

from pathlib import Path
import tempfile
import unittest

from scripts import corridor_replay, focus_replay, group_replay


class TestExperimentalScope(unittest.TestCase):
    def test_replays_remain_usable_but_are_labeled_exploratory(self):
        with tempfile.TemporaryDirectory(prefix='blacklight-exploratory-') as temporary:
            root = Path(temporary).resolve()
            if (not root.is_relative_to(Path(tempfile.gettempdir()).resolve())
                    or not root.name.startswith('blacklight-exploratory-')):
                raise AssertionError('Unexpected temporary directory')
            cases = (
                ('focus', lambda output: focus_replay.replay('dev', 'M3', 'F0', 'hammer', 0, output)),
                ('group', lambda output: group_replay.replay(
                    'dev', group_replay.scenarios()[0][0], group_replay.POLICIES[0].name, 0, output)),
                ('corridor', lambda output: corridor_replay.replay(
                    'dev', 12, corridor_replay.gunners()[0][0], corridor_replay.POLICIES[0].name, 0, output)),
            )
            for name, execute in cases:
                with self.subTest(name=name):
                    payload = execute(root / f'{name}.json')
                    self.assertEqual(payload['evidence_scope'], 'exploratory_uncertified')


if __name__ == '__main__':
    unittest.main()
