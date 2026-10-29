from dataclasses import replace
import unittest

from experimental.ram_trigger import Approach, ram_triggered
from combatants.runner import run_duel
from scripts.current_study_holdout import INPUTS, holdout_configurations


class RamTriggerTests(unittest.TestCase):
    def setUp(self):
        self.first = Approach('Victor', 'atirador', 2, 'movement', 10, 5, 5)
        self.second = Approach('Victor', 'atirador', 2, 'standard', 5, 1, 5)

    def trigger(self, first=None, second=None, *, reaction=True, able=True):
        return ram_triggered(first or self.first, second or self.second,
                             reaction_available=reaction, able_to_act=able)

    def test_full_speed_followed_by_standard_to_contact(self):
        self.assertTrue(self.trigger())

    def test_stops_before_full_speed_or_outside_contact(self):
        self.assertFalse(self.trigger(Approach('Victor', 'atirador', 2, 'movement', 9, 5, 5)))
        self.assertFalse(self.trigger(second=replace(self.second, after=2)))

    def test_wrong_turn_actor_target_action_or_discontinuous_motion(self):
        for changed in (replace(self.second, actor='terceiro'), replace(self.second, target='outro'),
                        replace(self.second, turn=3), replace(self.second, action='movement'),
                        replace(self.second, before=4)):
            with self.subTest(changed=changed):
                self.assertFalse(self.trigger(second=changed))

    def test_reaction_or_ability_to_act_missing(self):
        self.assertFalse(self.trigger(reaction=False))
        self.assertFalse(self.trigger(able=False))

    def test_invalid_or_forged_segment_rejected(self):
        for kwargs in ({'speed': True}, {'after': 0}, {'before': 20}, {'action': 'retreat'},
                       {'actor': 'atirador'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                replace(self.first, **kwargs)
        with self.assertRaises(ValueError):
            self.trigger(reaction=1)

    def test_real_audited_trace_contains_a_potential_trigger(self):
        hero, policies, scenarios = holdout_configurations(tuple(path.read_bytes() for path in INPUTS))
        foe, policy, distance, board = scenarios['gunner_open']
        result = run_duel(hero, foe, policies['hammer_fast_hammer'], policy,
                          seed=987654, initial_distance=distance, battlefield=board)
        self.assertEqual(result['audit_issues'], [])
        turn = [event for event in result['result']['log']
                if event['round'] == 2 and event.get('actor') == hero.name]
        self.assertGreater(next(event['reactions'] for event in turn if event['type'] == 'turn_start'), 0)
        moves = [event for event in turn if event['type'] == 'movement']
        self.assertEqual(len(moves), 2)
        first, second = (Approach(hero.name, foe.name, 2,
                                  'standard' if event['as_standard'] else 'movement',
                                  event['distance_before'], event['distance_after'], 5)
                         for event in moves)
        self.assertTrue(ram_triggered(first, second, reaction_available=True, able_to_act=True))
        self.assertFalse(any(event['type'] == 'attack' for event in turn))
