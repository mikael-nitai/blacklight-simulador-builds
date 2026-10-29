import json
from pathlib import Path
import unittest

from combatants.sheets import parse_sheet


class CrossbonesEvidenceTests(unittest.TestCase):
    def test_printed_sheet_is_preserved_as_non_executable_evidence(self):
        path = Path(__file__).resolve().parents[1] / 'character_evidence/crossbones_core_p155.json'
        evidence = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual((evidence['source']['printed_page'], evidence['source']['pdf_page']), (155, 156))
        self.assertEqual((evidence['rank'], evidence['health'], evidence['focus']), (3, 90, 90))
        self.assertEqual(evidence['karma_printed'], '—')
        self.assertEqual(evidence['initiative_printed'], '+2E')
        self.assertEqual((evidence['abilities']['agility']['score'],
                          evidence['abilities']['agility']['noncombat']), (5, 7))
        self.assertEqual(len(evidence['powers']['Ranged Weapons']), 8)
        self.assertIn('Double Tap', evidence['powers']['Ranged Weapons'])
        self.assertIn('Slow-Motion Dodge', evidence['powers']['Basic'])
        self.assertEqual((evidence['weapon_reference']['range_spaces'],
                          evidence['weapon_reference']['close_range_trouble_max_spaces']), (10, 5))
        with self.assertRaises(ValueError):
            parse_sheet(evidence)
