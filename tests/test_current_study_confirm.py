"""Gates around the locked current-rule confirmation configuration."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from combatants.runner import run_batch
from scripts import current_study_confirm as confirm
from scripts.current_study_dev import MASTER_SEED as DEV_SEED


class TestCurrentStudyConfirm(unittest.TestCase):
    def test_frozen_development_selection_matches_preregistered_finalists(self):
        selection = confirm.validated_selection()
        self.assertEqual(tuple(selection['finalists']), confirm.FINALISTS)
        self.assertEqual(confirm.POLICIES, ('bare', 'hammer', 'hammer_fast_hammer', 'hammer_fast_blade'))
        self.assertEqual(confirm.N_PER_CELL, 10000)
        self.assertNotEqual(confirm.MASTER_SEED, DEV_SEED)

    def test_changed_selection_and_existing_destination_are_rejected(self):
        with TemporaryDirectory() as folder:
            selection = Path(folder) / 'selection.json'
            selection.write_text('{}', encoding='utf-8')
            with patch.object(confirm, 'SELECTION', selection), self.assertRaisesRegex(ValueError, 'bytes changed'):
                confirm.validated_selection()
            output = Path(folder) / 'already.json'
            output.write_text('preserve me', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                confirm.execute_cell('mirror', 'bare', n=1, output=output)
            self.assertEqual(output.read_text(encoding='utf-8'), 'preserve me')
        with self.assertRaises(ValueError):
            confirm.execute_cell('mirror', 'other', n=1)

    def test_preflight_cell_identity_matches_actual_runner(self):
        hero, candidates, scenarios = confirm.configurations(tuple(path.read_bytes() for path in confirm.INPUTS))
        for scenario, (opponent, opponent_policy, distance, board) in scenarios.items():
            for name in confirm.POLICIES:
                with self.subTest(scenario=scenario, policy=name):
                    expected = confirm.confirmation_cell_hash(hero, opponent, candidates[name],
                                                              opponent_policy, distance, board)
                    actual = run_batch(hero, opponent, candidates[name], opponent_policy,
                                       n=1, master_seed=confirm.MASTER_SEED, initial_distance=distance,
                                       max_rounds=30, battlefield=board, extended_metrics=True)
                    self.assertEqual(actual['cell_sha256'], expected)
