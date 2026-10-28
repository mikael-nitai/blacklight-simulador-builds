"""Synthetic rule changes exercise isolation without changing table rules."""

from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from blacklight.audit import audit_profiled_log
from blacklight.engine import Action, Duel, Profile, blacklight_profile
from blacklight.mechanics_contract import compare_recorded_contracts, mechanics_digest
from blacklight.policies import ATTACK
from blacklight.pool_damage import roll_damage_pool
from blacklight.rulesets import CURRENT_RULESET
from combatants.actions import ActionRegistry, DEFAULT_ACTIONS, DO_THIS_ALL_DAY
from combatants.runner import _engine_metadata, _source_manifest
from combatants.split_fast import FastAction, SplitFastDuel, SplitFastPolicy


class FixedDice:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        value = next(self.values)
        if not low <= value <= high:
            raise AssertionError('Invalid predetermined die')
        return value


class HypotheticalFastDuel(SplitFastDuel):
    """Test-only new revision: add two to the Fast damage ability."""
    table_ruleset = 'test_only_fast_plus_two'
    execution_scope = 'experimental_rule_variant'

    def _roll_damage_component(self, **parameters):
        parameters = dict(parameters)
        if parameters['fast_strikes']:
            parameters['ability'] += 2
        return super()._roll_damage_component(**parameters)


class HypotheticalReactionsDuel(SplitFastDuel):
    """Test-only new revision: at most one reaction each round."""
    table_ruleset = 'test_only_one_reaction'
    execution_scope = 'experimental_rule_variant'

    def _reset_reactions_for_round(self):
        for fighter in self.fighters:
            fighter.reactions = 1
            fighter.reacted_to.clear()
            self._record('reaction_reset', ('ACT-03', 'ACT-04'),
                         actor=fighter.profile.name, reactions=1)


def combat(registry=DEFAULT_ACTIONS, *, seed=12, engine=SplitFastDuel):
    hero = replace(blacklight_profile(), heroic=False)
    foe = Profile('Target', 3, 1000, 90, 4, 2, 3, 2, 14, 12, 5)
    policy = SplitFastPolicy('fixed', edge_mode='decline', riposte=False)
    battle = engine((hero, foe), (policy, ATTACK), seed=seed,
                    action_registry=registry, audit=True)
    return battle, (hero, foe)


def contract_for(registry=DEFAULT_ACTIONS, *, ruleset=CURRENT_RULESET):
    # The alternative registry is exercised only in this test; the standard
    # runner does not expose it as a certified table revision.
    with patch('combatants.runner.DEFAULT_ACTIONS', registry):
        metadata = _engine_metadata(CURRENT_RULESET)
    sources = _source_manifest((ATTACK, ATTACK))
    record = {'table_ruleset': ruleset,
              'registered_action_modules': metadata['registered_action_modules'],
              'source_sha256': sources}
    record['mechanics_contract_sha256'] = mechanics_digest(
        ruleset, record['registered_action_modules'], sources)
    return record


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
        self.assertEqual(compare_recorded_contracts(
            contract_for(), contract_for(alternative))['status'], 'different_recorded_contracts')
        historical = json.loads((Path(__file__).resolve().parents[1] / 'results' /
                                 'split_fast_v3_blade_effects_demo.json').read_text(encoding='utf-8'))
        self.assertEqual(compare_recorded_contracts(
            historical, contract_for(alternative))['status'], 'unverified_missing_contract')

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

    def test_isolated_fast_revision_leaves_both_existing_versions_unchanged(self):
        def current_strike(engine, action):
            battle, profiles = combat(engine=engine)
            battle.round, battle.active_actor = 1, 0
            battle._reset_reactions_for_round()
            battle.fighters[0].standard_available = True
            battle.rng = FixedDice([6] * 12)
            battle.damage_rng = FixedDice([1] * 50)
            battle._act(0, action)
            return battle, profiles

        def historical_strike():
            _, profiles = combat()
            policy = SplitFastPolicy('old-control', edge_mode='decline', riposte=False)
            battle = Duel(profiles, (policy, ATTACK), seed=12, audit=True)
            battle.round, battle.active_actor = 1, 0
            battle._reset_reactions_for_round()
            battle.fighters[0].standard_available = True
            battle.rng = FixedDice([6] * 12)
            battle.damage_rng = FixedDice([1] * 50)
            battle._act(0, Action('fast_strikes'))
            return battle.log

        old_before = historical_strike()
        action = FastAction('fast_strikes', effect_limb=0)
        original, profiles = current_strike(SplitFastDuel, action)
        variant, _ = current_strike(HypotheticalFastDuel, action)
        original_again, _ = current_strike(SplitFastDuel, action)
        self.assertEqual(old_before, historical_strike())
        self.assertEqual(original.log, original_again.log)
        self.assertEqual((1000 - original.fighters[1].health,
                          1000 - variant.fighters[1].health), (42, 44))
        self.assertTrue(audit_profiled_log(variant.log, profiles, ruleset=CURRENT_RULESET))
        plain, _ = current_strike(SplitFastDuel, Action('melee'))
        variant_plain, _ = current_strike(HypotheticalFastDuel, Action('melee'))
        self.assertEqual(plain.log, variant_plain.log)
        self.assertEqual(compare_recorded_contracts(
            contract_for(), contract_for(ruleset=HypotheticalFastDuel.table_ruleset))['status'],
            'different_rulesets')

    def test_isolated_reaction_revision_changes_the_second_reaction_only(self):
        hero = replace(blacklight_profile(), heroic=False)
        foe = replace(hero, name='Opponent')
        defender = SplitFastPolicy('defender', shield_react=True, riposte=True, edge_mode='decline')
        attacker = SplitFastPolicy('attacker', edge_mode='decline', riposte=False)

        def encounter(engine):
            battle = engine((hero, foe), (defender, attacker), seed=1, audit=True)
            battle.round, battle.active_actor = 1, 1
            battle._reset_reactions_for_round()
            battle.fighters[1].standard_available = True
            # First limb hits, second misses; defender can Shield then Riposte.
            battle.rng = FixedDice([6, 6, 6, 2, 2, 2, 6, 6, 6])
            battle.damage_rng = FixedDice([1] * 100)
            battle._act(1, FastAction('fast_strikes', effect_limb=0))
            return battle

        baseline = encounter(SplitFastDuel)
        variant = encounter(HypotheticalReactionsDuel)
        baseline_again = encounter(SplitFastDuel)
        self.assertEqual(baseline.log, baseline_again.log)
        self.assertEqual((baseline.fighters[0].ripostes, variant.fighters[0].ripostes), (1, 0))
        self.assertTrue(any('reaction budget' in issue for issue in
                            audit_profiled_log(variant.log, (hero, foe), ruleset=CURRENT_RULESET)))
        no_reaction = replace(defender, shield_react=False, riposte=False)
        for seed in range(10):
            original = SplitFastDuel((hero, foe), (no_reaction, attacker), seed=seed, audit=True).run()
            modified = HypotheticalReactionsDuel((hero, foe), (no_reaction, attacker),
                                                seed=seed, audit=True).run()
            self.assertEqual((original.outcome, original.final_health, original.final_focus),
                             (modified.outcome, modified.final_health, modified.final_focus), seed)
            self.assertEqual([e for e in original.log if e['type'] == 'attack'],
                             [e for e in modified.log if e['type'] == 'attack'], seed)
        self.assertEqual(compare_recorded_contracts(
            contract_for(), contract_for(ruleset=HypotheticalReactionsDuel.table_ruleset))['status'],
            'different_rulesets')


if __name__ == '__main__':
    unittest.main()
