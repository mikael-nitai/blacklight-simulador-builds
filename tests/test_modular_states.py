"""Source-based state activation oracles and replay equivalence."""

from dataclasses import replace
from itertools import product
import unittest

from blacklight.engine import Action, Duel, IllegalAction, Profile, blacklight_profile
from blacklight.policies import ATTACK, RulePolicy, STANCE
from combatants.actions import (ActionPlan, ActionRegistry, ActivateState,
                                CapabilityRequirement, CombatState, RestoreHealth,
                                StateActivation, ATTACK_STANCE, DO_THIS_ALL_DAY)
from combatants.modular_duel import ModularDuel


class SequenceRNG:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        value = next(self.values)
        assert low <= value <= high
        return value


def enemy():
    return Profile('Other', 3, 90, 60, 4, 2, 3, 2, 14, 12, 5)


def game(cls=ModularDuel, *, registry=None, player=None):
    options = {} if registry is None else {'action_registry': registry}
    policy = replace(ATTACK, edge_mode='decline')
    battle = cls((player or blacklight_profile(), enemy()), (policy, ATTACK),
                  seed=8, audit=True, **options)
    battle.round = 1
    battle.active_actor = 0
    battle.fighters[0].standard_available = True
    return battle


class TestModularStates(unittest.TestCase):
    def test_zero_cost_actions_work_without_positive_focus(self):
        expected = {'stance': ('stance', 'stance', {'active': True}),
                    'shield': ('shield_active', 'shield_activate', {'cost': 'standard'}),
                    'dodge': ('dodging', 'dodge', {'active_until_next_turn': True})}
        for kind, focus in product(expected, (90, 0, -5)):
            old, new = game(Duel), game()
            for battle in (old, new):
                battle.fighters[0].focus = focus
                battle._act(0, Action(kind))
            attribute, event_type, fields = expected[kind]
            self.assertTrue(getattr(new.fighters[0], attribute))
            self.assertEqual(new.fighters[0].focus, focus)
            self.assertFalse(new.fighters[0].standard_available)
            self.assertEqual(new.log, old.log)
            self.assertEqual([event['type'] for event in new.log], [event_type])
            for key, value in fields.items():
                self.assertEqual(new.log[0][key], value)

    def test_power_and_weapon_requirements_are_independent(self):
        original = blacklight_profile()
        player = replace(original, powers=original.powers - {'attack_stance'},
                         weapons=original.weapons - {'shield'})
        battle = game(player=player)
        self.assertNotIn(Action('stance'), battle.legal_actions(0))
        self.assertNotIn(Action('shield'), battle.legal_actions(0))
        self.assertIn(Action('dodge'), battle.legal_actions(0))
        for action in (Action('stance'), Action('shield')):
            with self.assertRaises(IllegalAction):
                battle._act(0, action)
        self.assertEqual(battle.log, [])
        self.assertTrue(battle.fighters[0].standard_available)

    def test_state_eligibility_grid_matches_reference(self):
        for stance, shield, dodge, focus in product((False, True), (False, True),
                                                    (False, True), (-5, 0, 1, 5, 6, 90)):
            old, new = game(Duel), game()
            for battle in (old, new):
                fighter = battle.fighters[0]
                fighter.stance, fighter.shield_active, fighter.dodging = stance, shield, dodge
                fighter.focus = focus
            self.assertEqual(new.legal_actions(0), old.legal_actions(0))
            self.assertEqual(Action('stance') in new.legal_actions(0), not stance)
            self.assertEqual(Action('shield') in new.legal_actions(0), not shield)
            self.assertIn(Action('dodge'), new.legal_actions(0))

    def test_dodge_trouble_and_expiration_use_existing_lifecycle(self):
        battle = game()
        battle._act(0, Action('dodge'))
        battle.rng = SequenceRNG([6, 6, 6, 6])
        battle.damage_rng = SequenceRNG([2] * 20)
        battle._attack(1, 'melee')
        attack = next(row for row in battle.log if row['type'] == 'attack')
        self.assertEqual((attack['troubles'], attack['edges']), (1, 0))
        battle.active_actor = None
        battle.policies = (RulePolicy('wait', always_wait=True), ATTACK)
        battle._turn(0)
        self.assertFalse(battle.fighters[0].dodging)
        self.assertTrue(any(row['type'] == 'dodge_end' for row in battle.log))

    def test_stance_changes_damage_bonus_but_not_hit_modifier(self):
        battle = game()
        battle._act(0, Action('stance'))
        battle.rng = SequenceRNG([6, 6, 6])
        battle.damage_rng = SequenceRNG([2] * 6)
        battle._attack(0, 'melee')
        attack = next(row for row in battle.log if row['type'] == 'attack')
        self.assertEqual((attack['check_modifier'], attack['ability_for_damage']), (6, 12))
        self.assertEqual(attack['calculated_damage'], 24)  # six dice of 2 + 12

    def test_standard_shield_feeds_existing_dr_and_free_deactivation(self):
        battle = game()
        battle._act(0, Action('shield'))
        battle.rng = SequenceRNG([6] * 6)
        battle.damage_rng = SequenceRNG([2] * 30)
        battle._attack(1, 'melee')
        first = next(row for row in battle.log if row['type'] == 'attack')
        self.assertEqual((first['reduction'], first['calculated_damage']), (3, 0))
        self.assertEqual(battle.fighters[0].health, 150)
        battle._attack(0, 'hammer')
        self.assertFalse(battle.fighters[0].shield_active)
        ended = next(row for row in battle.log if row['type'] == 'shield_deactivate')
        self.assertEqual(ended['cost'], 'free')

    def test_trait_requirement_can_register_a_state_definition(self):
        # Synthetic definition only, used to test the generic trait prerequisite.
        fixture = StateActivation(
            'fixture_mode', (CapabilityRequirement('trait', 'combat_reflexes'),),
            CombatState.DODGE, True, ('TEST-ONLY',), ('Synthetic registry test',))
        battle = game(registry=ActionRegistry((fixture,)))
        self.assertIn(Action('fixture_mode'), battle.legal_actions(0))
        battle._act(0, Action('fixture_mode'))
        self.assertTrue(battle.fighters[0].dodging)

    def test_unsupported_state_plans_fail_without_any_partial_effect(self):
        cases = (
            (0, 0, (ActivateState('health', ('TEST',)),)),
            (0, 0, (ActivateState(CombatState.SHIELD, (x for x in ())),)),
            (0, 0, (ActivateState(CombatState.DODGE, ()),)),
            (0, 0, (RestoreHealth(10, 'TEST'),)),
            (5, 1, (ActivateState(CombatState.SHIELD, ('TEST',)),)),
            (0, 0, (ActivateState(CombatState.DODGE, ('TEST',)),
                    ActivateState(CombatState.SHIELD, ('TEST',)))),
        )
        for cost, floor, effects in cases:
            class Malformed:
                kind = 'bad_state'
                requirements = (CapabilityRequirement('power', 'attack_stance'),)
                sources = ('Malformed state-plan test',)

                def available(self, context):
                    return (Action(self.kind, cost),)

                def plan(self, context, request):
                    return ActionPlan(self.kind, cost, floor, ('TEST',), effects)

            battle = game(registry=ActionRegistry((Malformed(),)))
            battle.fighters[0].health = 100
            with self.assertRaises(IllegalAction):
                battle._act(0, Action('bad_state', cost))
            fighter = battle.fighters[0]
            self.assertEqual((fighter.health, fighter.focus, fighter.stance,
                              fighter.shield_active, fighter.dodging,
                              fighter.standard_available),
                             (100, 90, False, False, False, True))
            self.assertEqual(battle.log, [])

    def test_state_policy_complete_replays_match_reference(self):
        player = blacklight_profile()
        policies = (STANCE, RulePolicy('standard_shield', weapon='hammer', shield_standard=True),
                    RulePolicy('dodge', dodge_below_health=150))
        for policy, distance, seed in product(policies, (1, 5, 12), range(20)):
            options = dict(seed=seed, initial_distance=distance, max_rounds=15, audit=True)
            old = Duel((player, enemy()), (policy, ATTACK), **options).run()
            new = ModularDuel((player, enemy()), (policy, ATTACK), **options).run()
            self.assertEqual(new, old, (policy.name, distance, seed))

    def test_review_invalid_definitions_are_rejected_before_registration(self):
        factories = (
            lambda: replace(ATTACK_STANCE, rules=['TEST']),
            lambda: replace(ATTACK_STANCE, rules=()),
            lambda: replace(ATTACK_STANCE, rules=(' ',)),
            lambda: replace(ATTACK_STANCE, sources=['source']),
            lambda: replace(ATTACK_STANCE, requirements=[]),
            lambda: replace(ATTACK_STANCE, requirements=(
                CapabilityRequirement('power', 'attack_stance'),
                CapabilityRequirement('power', 'attack_stance'))),
            lambda: replace(DO_THIS_ALL_DAY, cost_rules=['TEST']),
            lambda: replace(DO_THIS_ALL_DAY, healing_rule=''),
            lambda: replace(DO_THIS_ALL_DAY, sources=['source']),
            lambda: replace(DO_THIS_ALL_DAY, required_power=123),
            lambda: CapabilityRequirement('power', ' '),
        )
        for factory in factories:
            with self.assertRaises(ValueError):
                factory()

    def test_review_zero_cost_request_types_cannot_exploit_numeric_equality(self):
        for kind, invalid_focus in product(('stance', 'shield', 'dodge'), (0.0, False, 0j)):
            battle = game()
            with self.assertRaises(IllegalAction):
                battle._act(0, Action(kind, invalid_focus))
            fighter = battle.fighters[0]
            self.assertEqual((fighter.focus, fighter.standard_available,
                              fighter.stance, fighter.shield_active, fighter.dodging),
                             (90, True, False, False, False))
            self.assertEqual(battle.log, [])


if __name__ == '__main__':
    unittest.main()
