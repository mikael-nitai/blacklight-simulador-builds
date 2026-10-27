"""Manual cost/healing oracles and whole-combat refactor equivalence."""

from dataclasses import replace
import unittest

from blacklight.engine import Action, Duel, IllegalAction, blacklight_profile
from blacklight.experiment import scenarios, strategies, seed_for
from blacklight.policies import ATTACK
from combatants.actions import (ActionContext, ActionPlan, ActionRegistry,
                                CapabilityRequirement, DO_THIS_ALL_DAY,
                                FocusSelfHeal, RestoreHealth)
from combatants.modular_duel import ModularDuel


def battle(cls=ModularDuel, *, registry=None):
    player = blacklight_profile()
    foe = replace(player, name='Other')
    kwargs = {} if registry is None else {'action_registry': registry}
    game = cls((player, foe), (ATTACK, ATTACK), seed=10, audit=True, **kwargs)
    game.active_actor = 0
    game.fighters[0].standard_available = True
    return game


class TestModularActions(unittest.TestCase):
    def test_manual_rank_cost_limits_and_focus_floor(self):
        context = ActionContext(3, 100, 150, 90,
                                frozenset({'do_this_all_day'}))
        self.assertEqual([a.focus for a in DO_THIS_ALL_DAY.available(context)],
                         list(range(5, 16)))
        rank4 = replace(context, rank=4, focus=21)
        self.assertEqual([a.focus for a in DO_THIS_ALL_DAY.available(rank4)],
                         list(range(5, 21)))
        self.assertEqual(DO_THIS_ALL_DAY.available(replace(context, focus=5)), ())
        self.assertEqual(DO_THIS_ALL_DAY.available(replace(context, focus=6)),
                         (Action('heal', 5),))
        plan = DO_THIS_ALL_DAY.plan(rank4, Action('heal', 20))
        self.assertEqual((plan.focus_cost, plan.effects[0].amount), (20, 40))
        self.assertEqual(rank4.focus, 21)  # Building a plan cannot pay a cost.

    def test_capped_healing_and_condition_log_match_reference(self):
        old, new = battle(Duel), battle()
        for game in (old, new):
            game.fighters[0].health = 147
            game.fighters[0].bleeding = 5
            game._act(0, Action('heal', 5))
        self.assertEqual((new.fighters[0].health, new.fighters[0].focus,
                          new.fighters[0].healing_effective,
                          new.fighters[0].bleeding), (150, 85, 3, 0))
        self.assertEqual(new.log, old.log)
        self.assertEqual([row['type'] for row in new.log],
                         ['focus_spent', 'condition_end', 'heal'])

    def test_heal_at_maximum_does_not_clear_bleeding_without_effective_heal(self):
        game = battle()
        game.fighters[0].bleeding = 5
        game._act(0, Action('heal', 5))
        self.assertEqual((game.fighters[0].health, game.fighters[0].focus,
                          game.fighters[0].bleeding), (150, 85, 5))

    def test_invalid_costs_and_action_state_do_not_partially_mutate(self):
        for request in (Action('heal', 4), Action('heal', 16),
                        Action('heal', 5, offhand='hammer'), Action('heal', 5.0)):
            game = battle()
            state = (game.fighters[0].focus, game.fighters[0].health,
                     game.fighters[0].standard_available)
            with self.assertRaises(IllegalAction):
                game._act(0, request)
            self.assertEqual((game.fighters[0].focus, game.fighters[0].health,
                              game.fighters[0].standard_available), state)
            self.assertEqual(game.log, [])
        for invalid in ('wrong_turn', 'stunned', 'no_action', 'unconscious'):
            game = battle()
            if invalid == 'wrong_turn':
                game.active_actor = 1
            elif invalid == 'stunned':
                game.fighters[0].stunned_by = 1
            elif invalid == 'no_action':
                game.fighters[0].standard_available = False
            else:
                game.fighters[0].health = 0
            with self.assertRaises(IllegalAction):
                game._act(0, Action('heal', 5))
            self.assertEqual(game.fighters[0].focus, 90)
            self.assertEqual(game.log, [])

    def test_another_definition_in_same_effect_family_needs_no_engine_edit(self):
        # Synthetic fixture only: this is an extensibility test, not an RPG power.
        fixture = FocusSelfHeal(
            kind='fixture_heal', required_power='fixture_power', minimum_spend=1,
            maximum_spend_per_rank=1, minimum_focus_remaining=1,
            health_per_focus=1, cost_rules=('TEST-ONLY',),
            healing_rule='TEST-ONLY', sources=('Synthetic unit-test definition',))
        registry = ActionRegistry((DO_THIS_ALL_DAY, fixture))
        game = battle(registry=registry)
        profile = game.fighters[0].profile
        game.fighters[0].profile = replace(profile, powers=profile.powers | {'fixture_power'})
        game.fighters[0].health = 140
        self.assertIn(Action('fixture_heal', 2), game.legal_actions(0))
        game._act(0, Action('fixture_heal', 2))
        self.assertEqual((game.fighters[0].health, game.fighters[0].focus), (142, 88))

    def test_registry_duplicate_and_invalid_plan_fail_before_spending(self):
        with self.assertRaises(ValueError):
            ActionRegistry((DO_THIS_ALL_DAY, DO_THIS_ALL_DAY))

        class BadPlan:
            kind = 'bad_plan'
            requirements = (CapabilityRequirement('power', 'do_this_all_day'),)
            sources = ('Test malformed-module rejection',)

            def available(self, context):
                return (Action(self.kind, 5),)

            def plan(self, context, request):
                return ActionPlan(self.kind, 5, 1, ('TEST',), ('invalid effect',))

        game = battle(registry=ActionRegistry((BadPlan(),)))
        with self.assertRaises(IllegalAction):
            game._act(0, Action('bad_plan', 5))
        self.assertEqual((game.fighters[0].focus, game.fighters[0].standard_available),
                         (90, True))
        self.assertEqual(game.log, [])

    def test_missing_power_is_rejected_even_if_module_forgets_prerequisite(self):
        class MissingPower:
            kind = 'unowned'
            requirements = (CapabilityRequirement('power', 'absent_power'),)
            sources = ('Test prerequisite guard',)

            def available(self, context):
                return (Action(self.kind, 5),)

            def plan(self, context, request):
                raise AssertionError('Unowned ability should never reach planning')

        game = battle(registry=ActionRegistry((MissingPower(),)))
        self.assertNotIn(Action('unowned', 5), game.legal_actions(0))
        with self.assertRaises(IllegalAction):
            game._act(0, Action('unowned', 5))

    def test_review_regression_generators_and_empty_plans_are_atomic_failures(self):
        factories = (
            lambda: ActionPlan('fixture', 5, 1, ('TEST',),
                               (RestoreHealth(10, 'TEST') for _ in range(1))),
            lambda: ActionPlan('fixture', 5, 1, ('TEST',), ()),
            lambda: ActionPlan('fixture', 5, 1, (x for x in ()),
                               (RestoreHealth(10, 'TEST'),)),
            lambda: ActionPlan('fixture', 5, 1, ['TEST'],
                               (RestoreHealth(10, 'TEST'),)),
            lambda: ActionPlan('fixture', 6, 1, ('TEST',),
                               (RestoreHealth(10, 'TEST'),)),
            lambda: ActionPlan('fixture', 5, 0, ('TEST',),
                               (RestoreHealth(10, 'TEST'),)),
            lambda: {'action_kind': 'fixture'},
        )
        for factory in factories:
            class Malformed:
                kind = 'fixture'
                requirements = (CapabilityRequirement('power', 'do_this_all_day'),)
                sources = ('Malformed extension test',)

                def available(self, context):
                    return (Action(self.kind, 5),)

                def plan(self, context, request):
                    return factory()

            game = battle(registry=ActionRegistry((Malformed(),)))
            game.fighters[0].health = 50
            with self.assertRaises(IllegalAction):
                game._act(0, Action('fixture', 5))
            self.assertEqual((game.fighters[0].health, game.fighters[0].focus,
                              game.fighters[0].standard_available), (50, 90, True))
            self.assertEqual(game.log, [])

    def test_review_regression_invalid_requests_cannot_enter_legal_action_list(self):
        for emitted, focus in ((([],), 90),
                               ((Action('other_kind', 5),), 90),
                               ((Action('fixture', 16),), 90),
                               ((Action('fixture', 5),), 5),
                               ((Action('fixture', 5), Action('fixture', 5)), 90)):
            class BadAvailable:
                kind = 'fixture'
                requirements = (CapabilityRequirement('power', 'do_this_all_day'),)
                sources = ('Malformed request test',)

                def available(self, context):
                    return emitted

                def plan(self, context, request):
                    raise AssertionError('Invalid request must not reach planning')

            game = battle(registry=ActionRegistry((BadAvailable(),)))
            game.fighters[0].focus = focus
            with self.assertRaises(IllegalAction):
                game.legal_actions(0)
            self.assertEqual((game.fighters[0].focus,
                              game.fighters[0].standard_available), (focus, True))
            self.assertEqual(game.log, [])

    def test_complete_replays_match_frozen_engine_across_all_policies(self):
        for scenario in scenarios():
            profiles = (blacklight_profile(), scenario.opponent)
            for strategy in strategies():
                for index in range(20):
                    seed = seed_for('modular_refactor_gate', scenario.id,
                                    strategy.id, index)
                    kwargs = dict(seed=seed, initial_distance=scenario.distance,
                                  max_rounds=30, audit=True)
                    policies = (strategy.policy, scenario.policy)
                    old = Duel(profiles, policies, **kwargs).run()
                    new = ModularDuel(profiles, policies, **kwargs).run()
                    self.assertEqual(new, old,
                                     (scenario.id, strategy.id, index))


if __name__ == '__main__':
    unittest.main()
