import unittest
from copy import deepcopy

from blacklight.audit import audit_profiled_log
from blacklight.engine import Move
from blacklight.spatial_audit import audit_open_field_distance
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.runner import _require_engine_ruleset
from combatants.split_fast import SplitFastDuel
from experimental.ram_opportunity_duel import RamOpportunityDuel
from experimental.ram_opportunity_audit import audit_ram_opportunities
from scripts.current_study_holdout import INPUTS, holdout_configurations


class RamOpportunityDuelTests(unittest.TestCase):
    def setUp(self):
        hero, policies, scenarios = holdout_configurations(tuple(path.read_bytes() for path in INPUTS))
        foe, foe_policy, distance, _ = scenarios['gunner_open']
        self.profiles = (compile_duel(hero), compile_duel(foe))
        self.policies = (policies['hammer_fast_hammer'], foe_policy)
        self.distance = distance

    def battle(self, cls, seed=987654):
        return cls(self.profiles, self.policies, seed=seed, initial_distance=self.distance,
                   max_rounds=30, audit=True, action_registry=DEFAULT_ACTIONS)

    def test_real_duel_detects_opportunity_without_performing_attack(self):
        duel = self.battle(RamOpportunityDuel)
        result = duel.run()
        events = [event for event in result.log if event['type'] == 'ram_opportunity']
        self.assertTrue(events)
        event = next(item for item in events if item['actor'] == self.profiles[0].name and item['round'] == 2)
        self.assertEqual((event['first_before'], event['first_after'], event['second_after'], event['speed']),
                         (10, 5, 1, 5))
        self.assertGreater(event['reactions'], 0)
        self.assertEqual(audit_profiled_log(result.log, self.profiles, ruleset=duel.table_ruleset), [])
        self.assertEqual(audit_open_field_distance(result.log, self.distance), [])
        self.assertEqual(audit_ram_opportunities(result.log, self.profiles), [])

    def test_observer_does_not_change_existing_duel_replay(self):
        for seed in range(20):
            with self.subTest(seed=seed):
                baseline = self.battle(SplitFastDuel, seed).run()
                observed = self.battle(RamOpportunityDuel, seed).run()
                self.assertEqual(audit_ram_opportunities(observed.log, self.profiles), [])
                for field in ('winner', 'outcome', 'rounds', 'turns', 'final_health', 'final_focus', 'metrics'):
                    self.assertEqual(getattr(baseline, field), getattr(observed, field))
                strip = lambda log: [{key: value for key, value in event.items() if key != 'seq'}
                                     for event in log if event['type'] != 'ram_opportunity']
                self.assertEqual(strip(baseline.log), strip(observed.log))

    def test_no_opportunity_without_available_reaction(self):
        duel = self.battle(RamOpportunityDuel)
        actor = duel.fighters[0]
        duel.active_actor = 0
        duel.turn_counts[0] = 1
        duel.distance = 10
        actor.standard_available = actor.movement_available = True
        actor.reactions = 0
        duel._move(0, Move('approach', 5))
        duel._move(0, Move('approach', 5), as_standard=True)
        self.assertFalse(any(event['type'] == 'ram_opportunity' for event in duel.log))

    def test_experimental_scope_is_not_registered_as_certified_duel(self):
        self.assertNotEqual(RamOpportunityDuel.execution_scope, 'two_character_physical')
        with self.assertRaisesRegex(RuntimeError, 'experimental engine'):
            _require_engine_ruleset(RamOpportunityDuel, RamOpportunityDuel.table_ruleset, None)

    def test_independent_audit_rejects_missing_or_forged_marker(self):
        log = list(self.battle(RamOpportunityDuel).run().log)
        index = next(i for i, event in enumerate(log) if event['type'] == 'ram_opportunity')
        missing = deepcopy(log)
        missing.pop(index)
        self.assertTrue(audit_ram_opportunities(missing, self.profiles))
        for field, value in (('speed', 99), ('first_after', 1), ('reactions', 0),
                             ('second_after', True),
                             ('scope', 'attack completed')):
            with self.subTest(field=field):
                forged = deepcopy(log)
                forged[index][field] = value
                self.assertTrue(audit_ram_opportunities(forged, self.profiles))
        extra = deepcopy(log)
        extra.insert(index + 1, deepcopy(extra[index]))
        self.assertTrue(audit_ram_opportunities(extra, self.profiles))
