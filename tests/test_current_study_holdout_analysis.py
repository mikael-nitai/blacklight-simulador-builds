import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.current_study_holdout_analysis import load_holdout


class HoldoutAnalysisInputTests(unittest.TestCase):
    def test_rejects_confirmation_analysis_with_changed_input(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'analysis.json'
            path.write_text(json.dumps({'schema': 'blacklight-current-duel-confirmation-analysis-v1',
                                        'input_sha256': {'result': 'incorrect'}}), encoding='utf-8')
            with (patch('scripts.current_study_holdout_analysis.ANALYSIS', path),
                  patch('scripts.current_study_holdout_analysis.validated_selection', return_value={'input_sha256': {}}),
                  patch('scripts.current_study_holdout_analysis.load_confirmation', return_value=({}, {'result': 'expected'}, 'commit'))):
                with self.assertRaisesRegex(ValueError, 'does not match'):
                    load_holdout()

    def test_rejects_incomplete_previous_seed_inventory(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'analysis.json'
            path.write_text(json.dumps({'schema': 'blacklight-current-duel-confirmation-analysis-v1',
                                        'input_sha256': {}}), encoding='utf-8')
            with (patch('scripts.current_study_holdout_analysis.ANALYSIS', path),
                  patch('scripts.current_study_holdout_analysis.validated_selection', return_value={'input_sha256': {}}),
                  patch('scripts.current_study_holdout_analysis.load_confirmation', return_value=({}, {}, 'commit'))):
                with self.assertRaisesRegex(ValueError, 'seed inventory is incomplete'):
                    load_holdout()
