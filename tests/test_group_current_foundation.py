"""Forced checks for the interrupted current-rules fixed-contact group host.

These are narrow integration controls, not a certification of group combat.
"""

from copy import deepcopy
from dataclasses import asdict, replace
import unittest

from blacklight.audit import audit_profiled_log
from blacklight.engine import IllegalAction, Profile, blacklight_profile
from combatants.group import GroupBattle, GroupPolicy
from combatants.split_fast import FastAction


class FixedDice:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        value = next(self.values)
        if not low <= value <= high:
            raise AssertionError('Invalid predetermined die')
        return value


def target(name, *, dr=0, shield=False):
    return Profile(name, 3, 1000, 90, 4, 2, 3, 2, 14, 12, 5,
                   health_dr=dr, weapons=frozenset({'shield'}) if shield else frozenset())


def game(*, shields=False, teams=('heroes', 'enemies', 'enemies')):
    hero = replace(blacklight_profile(), heroic=False)
    profiles = (hero, target('Alvo A', dr=0 if shields else 1, shield=shields),
                target('Alvo B', dr=0 if shields else 2, shield=shields))
    hero_policy = GroupPolicy('hero', weapon='hammer', offhand='blade',
                              prefer_fast=True, split_targets=True,
                              effect_limb=0, edge_mode='decline')
    foe_policy = GroupPolicy('enemy', shield_react=shields, riposte=False)
    battle = GroupBattle(profiles, (hero_policy, foe_policy, foe_policy),
                         teams=teams, seed=1, audit=True)
    battle.round = 1
    battle._reset_reactions_for_round()
    battle.active_actor = 0
    battle.fighters[0].standard_available = True
    battle.damage_rng = FixedDice([1] * 50)
    return battle, profiles


class TestCurrentGroupFoundation(unittest.TestCase):
    def test_two_targets_keep_separate_damage_and_only_selected_effects(self):
        battle, profiles = game()
        # Hammer Fantastic against A; Blade ordinary hit against B.
        battle.rng = FixedDice([2, 1, 2, 6, 6, 6])
        battle._act(0, FastAction('hammer_fast', offhand='blade',
                                  effect_limb=0, targets=(1, 2)))
        a, b = battle.fighters[1:]
        # A: (8 - 1) dice, all six, +6 = 48. B: floor((7 - 2)/2)
        # dice, all six, +3 = 15. B receives no Blade Bleeding.
        self.assertEqual((1000 - a.health, 1000 - b.health), (48, 15))
        self.assertEqual((a.stunned_by, b.stunned_by, b.bleeding), (0, None, 0))
        checks = [e for e in battle.log if e['type'] == 'fast_limb_check']
        first_effect = next(e['seq'] for e in battle.log if e['type'] == 'condition_start')
        self.assertEqual([e['target'] for e in checks], ['Alvo A', 'Alvo B'])
        self.assertLess(max(e['seq'] for e in checks), first_effect)
        self.assertEqual(audit_profiled_log(battle.log, profiles), [])

        forged = deepcopy(battle.log)
        next(e for e in forged if e['type'] == 'fast_limb_check' and e['limb'] == 1)['target'] = 'Alvo A'
        self.assertTrue(audit_profiled_log(forged, profiles))

    def test_both_targets_can_activate_their_own_shield_before_damage(self):
        battle, profiles = game(shields=True)
        battle.rng = FixedDice([6, 6, 6, 6, 6, 6])
        battle._act(0, FastAction('hammer_fast', offhand='blade',
                                  effect_limb=0, targets=(1, 2)))
        self.assertEqual((1000 - battle.fighters[1].health, 1000 - battle.fighters[2].health),
                         (21, 15))
        shields = [e for e in battle.log if e['type'] == 'shield_activate']
        attacks = [e for e in battle.log if e['type'] == 'attack']
        self.assertEqual({e['actor'] for e in shields}, {'Alvo A', 'Alvo B'})
        self.assertLess(max(e['seq'] for e in shields), min(e['seq'] for e in attacks))
        self.assertEqual(audit_profiled_log(battle.log, profiles), [])

    def test_friendly_target_is_rejected_without_spending_the_action(self):
        battle, _ = game(teams=('heroes', 'heroes', 'enemies'))
        before = tuple(f.health for f in battle.fighters)
        with self.assertRaises(IllegalAction):
            battle._act(0, FastAction('hammer_fast', offhand='blade',
                                      effect_limb=0, targets=(1, 2)))
        self.assertTrue(battle.fighters[0].standard_available)
        self.assertEqual(tuple(f.health for f in battle.fighters), before)
        self.assertFalse(any(e['type'] == 'fast_use_start' for e in battle.log))

    def test_inactive_source_turn_advances_stun_and_heals_if_alive(self):
        battle, _ = game(teams=('heroes', 'heroes', 'enemies'))
        battle.active_actor = None
        battle.turn_counts[0] = 1
        battle._apply_stun(0, 2)
        battle.fighters[0].health = -1
        battle._inactive_turn(0)
        self.assertIsNone(battle.fighters[2].stunned_by)
        self.assertEqual(battle.fighters[0].health, 4)
        self.assertTrue(any(e['type'] == 'turn_skipped' and e['actor'] == 'Blacklight'
                            for e in battle.log))
        self.assertFalse(any(e['type'] == 'attack' for e in battle.log))

    def test_fixed_seed_group_replays_and_profiled_audits(self):
        hero = blacklight_profile()
        profiles = (hero, replace(hero, name='Enemy A'), replace(hero, name='Enemy B'))
        for split in (False, True):
            for selected in (0, 1):
                policies = (
                    GroupPolicy('hero', weapon='blade', offhand='hammer', prefer_fast=True,
                                split_targets=split, effect_limb=selected, shield_react=True),
                    GroupPolicy('a', weapon='hammer', prefer_fast=True, shield_react=True),
                    GroupPolicy('b', weapon='hammer', prefer_fast=True, shield_react=True),
                )
                for seed in range(25):
                    with self.subTest(split=split, selected=selected, seed=seed):
                        def run():
                            return GroupBattle(profiles, policies,
                                               teams=('heroes', 'enemies', 'enemies'),
                                               seed=seed, max_rounds=12, audit=True).run()
                        first = run()
                        self.assertEqual(first, run())
                        self.assertEqual(asdict(first)['evidence_scope'], 'experimental_group_uncertified')
                        self.assertEqual(audit_profiled_log(first.log, profiles), [])


if __name__ == '__main__':
    unittest.main()
