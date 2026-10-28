"""Forced reaction nesting and Blade retargeting in experimental group combat.

These small examples use manually chosen faces and expected action order, not
another copy of the engine's queue implementation.
"""

from dataclasses import replace
import unittest

from blacklight.audit import audit_profiled_log
from blacklight.engine import Profile, blacklight_profile
from combatants.group import GroupBattle, GroupPolicy
from combatants.split_fast import FastAction


MISS = (1, 2, 1)
HIT = (6, 6, 6)
FANTASTIC = (2, 1, 2)


class FixedDice:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        value = next(self.values)
        if not low <= value <= high:
            raise AssertionError('Face outside the die range')
        return value


def battle(*, hero_health=150, a_health=100, b_health=100, a_reflexes=False,
           weapon='hammer', hero_riposte=True, enemy_riposte=True):
    hero = replace(blacklight_profile(), max_health=hero_health, heroic=False)
    enemy_a = Profile('A', 3, a_health, 90, 4, 2, 3, 2, 14, 12, 5,
                      powers=frozenset({'riposte'}) if enemy_riposte else frozenset(),
                      traits=frozenset({'combat_reflexes'}) if a_reflexes else frozenset())
    enemy_b = replace(enemy_a, name='B', max_health=b_health, traits=frozenset())
    hero_policy = GroupPolicy('hero', weapon=weapon,
                              offhand='blade' if weapon == 'hammer' else 'hammer',
                              prefer_fast=True, split_targets=True, effect_limb=0,
                              edge_mode='decline', riposte=hero_riposte)
    enemy_policy = GroupPolicy('enemy', edge_mode='decline', riposte=enemy_riposte)
    profiles = (hero, enemy_a, enemy_b)
    result = GroupBattle(profiles, (hero_policy, enemy_policy, enemy_policy),
                         teams=('heroes', 'opponents', 'opponents'), seed=1, audit=True)
    result.round = 1
    result._reset_reactions_for_round()
    result.active_actor = 0
    result.fighters[0].standard_available = True
    result.damage_rng = FixedDice([1] * 100)  # each damage die has value six
    return result, profiles


def reaction_attacks(game):
    return [(event['actor'], event['target']) for event in game.log
            if event['type'] == 'attack' and event['reaction']]


class TestGroupReactionInterrupts(unittest.TestCase):
    def test_child_riposte_interrupts_before_other_pending_target(self):
        game, profiles = battle()
        game.rng = FixedDice(MISS * 6)
        game._act(0, FastAction('hammer_fast', offhand='blade',
                                effect_limb=0, targets=(1, 2)))
        self.assertEqual(reaction_attacks(game), [
            ('A', 'Blacklight'), ('Blacklight', 'A'),
            ('B', 'Blacklight'), ('Blacklight', 'B')])
        use_end = next(e['seq'] for e in game.log if e['type'] == 'fast_use_end')
        reacts = [e['seq'] for e in game.log if e['type'] == 'reaction_spent']
        self.assertLess(use_end, min(reacts))
        self.assertEqual(audit_profiled_log(game.log, profiles), [])

    def test_nested_reaction_knockout_cancels_other_pending_target(self):
        game, profiles = battle(hero_health=10, a_reflexes=True)
        # Both arms fail; A misses; Victor misses its interrupting Riposte;
        # A's second reaction hits for (3 - Sturdy 1)d6 + 4 = 16.
        game.rng = FixedDice(MISS * 4 + HIT)
        game._act(0, FastAction('hammer_fast', offhand='blade',
                                effect_limb=0, targets=(1, 2)))
        self.assertEqual(reaction_attacks(game), [
            ('A', 'Blacklight'), ('Blacklight', 'A'), ('A', 'Blacklight')])
        self.assertEqual(game.fighters[0].health, -6)
        self.assertEqual(game.fighters[2].ripostes, 0)
        self.assertEqual(audit_profiled_log(game.log, profiles), [])

    def test_first_direct_riposte_knockout_cancels_other_pending_target(self):
        game, profiles = battle(hero_health=10)
        game.rng = FixedDice(MISS * 2 + HIT)
        game._act(0, FastAction('hammer_fast', offhand='blade',
                                effect_limb=0, targets=(1, 2)))
        self.assertEqual(reaction_attacks(game), [('A', 'Blacklight')])
        self.assertEqual(game.fighters[0].health, -6)
        self.assertEqual(game.fighters[2].ripostes, 0)
        self.assertEqual(audit_profiled_log(game.log, profiles), [])

    def test_blade_bonus_retargets_surviving_enemy_after_first_is_down(self):
        game, profiles = battle(a_health=40, b_health=1000, weapon='blade',
                                hero_riposte=False, enemy_riposte=False)
        game.rng = FixedDice(FANTASTIC + HIT * 3)
        game._act(0, FastAction('blade_fast', offhand='hammer',
                                effect_limb=0, targets=(1, 2)))
        declarations = [(e['targets'], e['bonus_action']) for e in game.log
                        if e['type'] == 'fast_use_start']
        self.assertEqual(declarations, [(['A', 'B'], False), (['B', 'B'], True)])
        self.assertEqual(game.fighters[0].blade_bonus_actions, 1)
        self.assertEqual((game.fighters[1].health, game.fighters[2].health), (-8, 925))
        self.assertEqual(audit_profiled_log(game.log, profiles), [])


if __name__ == '__main__':
    unittest.main()
