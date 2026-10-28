"""The independent log checker must detect arithmetic edits and bad ledgers."""

from copy import deepcopy
from dataclasses import replace
import unittest

from blacklight.audit import audit_log
from blacklight.engine import Duel, Move, blacklight_profile
from blacklight.policies import ATTACK, BLADE_HAMMER_FAST, HAMMER


class TestAudit(unittest.TestCase):
    @staticmethod
    def battle(seed):
        a = blacklight_profile()
        b = replace(a, name="Enemy")
        return Duel((a, b), (BLADE_HAMMER_FAST, HAMMER), seed=seed,
                    audit=True).run()

    def test_short_complete_logs_are_self_consistent(self):
        for seed in range(100):
            result = self.battle(seed)
            self.assertEqual(audit_log(result.log,
                                       {"Blacklight": 150, "Enemy": 150},
                                       {"Blacklight": 90, "Enemy": 90}), [])

    def test_checker_rejects_corrupted_damage(self):
        result = self.battle(0)
        log = [dict(event) for event in result.log]
        attack = next(event for event in log if event["type"] == "attack"
                      and event["success"])
        attack["calculated_damage"] += 1
        issues = audit_log(log, {"Blacklight": 150, "Enemy": 150},
                           {"Blacklight": 90, "Enemy": 90})
        self.assertTrue(any("damage arithmetic mismatch" in issue for issue in issues))

    def test_checker_rejects_second_reaction_reset_in_same_round(self):
        result = self.battle(0)
        log = [dict(event) for event in result.log]
        reset = next(event for event in log if event["type"] == "reaction_reset")
        log.insert(log.index(reset) + 1, dict(reset))
        for seq, event in enumerate(log, 1):
            event["seq"] = seq
        issues = audit_log(log, {"Blacklight": 150, "Enemy": 150},
                           {"Blacklight": 90, "Enemy": 90})
        self.assertTrue(any("duplicate reaction reset" in issue for issue in issues))

    def test_checker_rejects_consistent_but_falsified_reaction_capacity(self):
        hero = blacklight_profile()
        foe = replace(hero, name='Enemy')
        wait = replace(ATTACK, always_wait=True)
        result = Duel((hero, foe), (wait, wait), seed=9, max_rounds=2, audit=True).run()
        log = deepcopy(result.log)
        for event in log:
            if event['type'] in ('reaction_reset', 'turn_start'):
                event['reactions'] = 99
        health = {hero.name: hero.max_health, foe.name: foe.max_health}
        focus = {hero.name: hero.max_focus, foe.name: foe.max_focus}
        # Both combatants have Combat Reflexes: 1 normal + 1 extra reaction.
        limits = {hero.name: 2, foe.name: 2}
        self.assertEqual(audit_log(result.log, health, focus, reaction_limits=limits), [])
        issues = audit_log(log, health, focus, reaction_limits=limits)
        self.assertTrue(any('reaction budget' in issue for issue in issues))

    def test_checker_rejects_fractional_or_excessive_movement(self):
        hero = blacklight_profile()
        foe = replace(hero, name='Enemy')
        duel = Duel((hero, foe), (ATTACK, ATTACK), seed=1, initial_distance=3, audit=True)
        duel.round = 1
        duel.active_actor = 0
        duel.fighters[0].movement_available = True
        duel._move(0, Move('retreat', 1))
        health = {hero.name: hero.max_health, foe.name: foe.max_health}
        focus = {hero.name: hero.max_focus, foe.name: foe.max_focus}
        limits = {hero.name: 5, foe.name: 5}
        self.assertEqual(audit_log(duel.log, health, focus, movement_limits=limits), [])
        for bad_steps in (0.5, True, 6):
            log = deepcopy(duel.log)
            log[0]['steps'] = bad_steps
            issues = audit_log(log, health, focus, movement_limits=limits)
            self.assertTrue(any('invalid movement' in issue for issue in issues), bad_steps)

    def test_checker_rejects_action_after_actor_becomes_unconscious(self):
        log = [
            {'seq': 1, 'round': 1, 'bonus_round': False, 'type': 'condition_tick',
             'actor': 'A', 'health_before': 5, 'health_after': 0, 'damage': 5},
            {'seq': 2, 'round': 1, 'bonus_round': False, 'type': 'movement',
             'actor': 'A', 'direction': 'retreat', 'steps': 1, 'as_standard': False},
        ]
        issues = audit_log(log, {'A': 5}, {'A': 5}, movement_limits={'A': 5})
        self.assertTrue(any('unconscious actor' in issue for issue in issues))


if __name__ == "__main__":
    unittest.main()
