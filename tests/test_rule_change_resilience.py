"""Synthetic rule changes exercise isolation without changing table rules."""

from dataclasses import replace
import unittest
from unittest.mock import patch

from blacklight.audit import audit_profiled_log
from blacklight.engine import Action, Profile, blacklight_profile
from blacklight.policies import ATTACK
from blacklight.pool_damage import roll_damage_pool
from combatants.actions import ActionRegistry, DEFAULT_ACTIONS, DO_THIS_ALL_DAY
from combatants.split_fast import FastAction, SplitFastDuel, SplitFastPolicy


class FixedDice:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        value = next(self.values)
        if not low <= value <= high:
            raise AssertionError('Invalid predetermined die')
        return value


def combat(registry=DEFAULT_ACTIONS, *, seed=12):
    hero = replace(blacklight_profile(), heroic=False)
    foe = Profile('Target', 3, 1000, 90, 4, 2, 3, 2, 14, 12, 5)
    policy = SplitFastPolicy('fixed', edge_mode='decline', riposte=False)
    battle = SplitFastDuel((hero, foe), (policy, ATTACK), seed=seed,
                           action_registry=registry, audit=True)
    return battle, (hero, foe)


class TestRuleChangeResilience(unittest.TestCase):
    def test_hypothetical_healing_definition_is_local_and_other_fights_match(self):
        changed_heal = replace(DO_THIS_ALL_DAY, health_per_focus=3,
                               sources=('Synthetic rule-change test only',))
        alternative = ActionRegistry(tuple(
            changed_heal if module.kind == 'heal' else module
            for module in DEFAULT_ACTIONS.modules.values()))
        outcomes = []
        for registry in (DEFAULT_ACTIONS, alternative):
            battle, _ = combat(registry)
            battle.active_actor = 0
            battle.fighters[0].standard_available = True
            battle.fighters[0].health = 100
            battle._act(0, Action('heal', 5))
            outcomes.append((battle.fighters[0].health, battle.fighters[0].focus))
        self.assertEqual(outcomes, [(110, 85), (115, 85)])

        # Neither policy requests healing. A rule change to that module must
        # leave these complete same-seed combat records identical.
        for seed in range(10):
            games = []
            for registry in (DEFAULT_ACTIONS, alternative):
                battle, _ = combat(registry, seed=seed)
                games.append(battle.run())
            self.assertEqual(games[0], games[1], seed)

    def test_hypothetical_fast_damage_change_is_detected_and_melee_stays_equal(self):
        def alternative_damage(rng, **kwargs):
            if kwargs['fast_strikes']:
                kwargs['ability'] += 2  # Synthetic counterfactual, never the table rule.
            return roll_damage_pool(rng, **kwargs)

        def strike(action, altered):
            battle, profiles = combat()
            battle.round = 1
            battle._reset_reactions_for_round()
            battle.active_actor = 0
            battle.fighters[0].standard_available = True
            battle.rng = FixedDice([6] * 12)
            battle.damage_rng = FixedDice([1] * 50)
            if altered:
                with patch('blacklight.engine.roll_damage_pool', side_effect=alternative_damage):
                    battle._act(0, action)
            else:
                battle._act(0, action)
            return battle, audit_profiled_log(battle.log, profiles)

        plain, issues = strike(Action('melee'), False)
        changed_plain, changed_issues = strike(Action('melee'), True)
        self.assertEqual((issues, changed_issues), ([], []))
        self.assertEqual(plain.log, changed_plain.log)

        original, original_issues = strike(FastAction('fast_strikes', effect_limb=0), False)
        changed, changed_issues = strike(FastAction('fast_strikes', effect_limb=0), True)
        self.assertEqual(original_issues, [])
        self.assertEqual(1000 - original.fighters[1].health, 42)
        self.assertEqual(1000 - changed.fighters[1].health, 44)
        self.assertTrue(any('component dice ledger mismatch' in issue for issue in changed_issues))


if __name__ == '__main__':
    unittest.main()
