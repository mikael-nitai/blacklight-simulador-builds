from dataclasses import replace
from copy import deepcopy
import unittest

from blacklight.engine import IllegalAction, Move, Profile
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.runner import _require_engine_ruleset
from combatants.split_fast import SplitFastPolicy
from experimental.ram_checkpoint_duel import RamCheckpointDuel
from experimental.ram_checkpoint_audit import audit_ram_checkpoint
from experimental.ram_opportunity_audit import audit_ram_opportunities
from experimental.ram_rolled import audit_rolled_table_ram
from scripts.current_study_holdout import INPUTS, holdout_configurations


def profile(name, melee, *, health=100, dr=0, initiative=0, **kwargs):
    return Profile(name, 3, health, 60, melee, 0, 5, 2, 10 + melee, 10, 5,
                   health_dr=dr, initiative_modifier=initiative, **kwargs)


class StationaryPolicy(SplitFastPolicy):
    def choose_move(self, observation):
        return Move()


class RamCheckpointDuelTests(unittest.TestCase):
    def setUp(self):
        self.attacker = profile('Atacante', 4, dr=1, initiative=100)
        self.defender = profile('Alvo', 2, dr=2)
        self.policies = (SplitFastPolicy('approach', knockback_stance=False),
                         StationaryPolicy('wait', always_wait=True, knockback_stance=False))

    def checkpoint(self, seed=1, attacker=None, defender=None, distance=10):
        profiles = (attacker or self.attacker, defender or self.defender)
        duel = RamCheckpointDuel(profiles, self.policies, seed=seed, initial_distance=distance,
                                 max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS,
                                 ram_actor=0)
        return duel, duel.run_to_opportunity()

    def test_real_movement_to_attack_reaction_and_record(self):
        duel, checkpoint = self.checkpoint()
        self.assertEqual(checkpoint['status'], 'opportunity')
        self.assertEqual(audit_ram_opportunities(checkpoint['log'], (self.attacker, self.defender)), [])
        result = duel.resolve_bare_ram()
        self.assertEqual(result['status'], 'resolved_checkpoint')
        record = result['transaction']
        self.assertEqual(audit_rolled_table_ram(record), [])
        self.assertEqual(record['parameters']['self_pool'], 'separate')
        self.assertEqual(record['before']['reactions'] - record['after']['reactions'], 1)
        self.assertEqual(duel.fighters[0].health, record['after']['attacker_health'])
        self.assertEqual(duel.fighters[1].health, record['after']['target_health'])
        self.assertEqual(result['log'][-1]['type'], 'ram_checkpoint_resolved')
        self.assertEqual(audit_ram_checkpoint(result['log'], (self.attacker, self.defender),
                                              initial_distance=10, ruleset=duel.table_ruleset, seed=duel.seed), [])
        with self.assertRaises(IllegalAction):
            duel.resolve_bare_ram()

    def test_seeded_checkpoint_replays_exactly(self):
        first, _ = self.checkpoint(seed=9)
        second, _ = self.checkpoint(seed=9)
        self.assertEqual(first.resolve_bare_ram(), second.resolve_bare_ram())

    def test_hit_miss_and_fantastic_are_all_tested(self):
        seen = set()
        for seed in range(80):
            duel, _ = self.checkpoint(seed=seed)
            resolved = duel.resolve_bare_ram()
            record = resolved['transaction']
            self.assertEqual(audit_rolled_table_ram(record), [])
            self.assertEqual(audit_ram_checkpoint(resolved['log'], (self.attacker, self.defender),
                                                  initial_distance=10, ruleset=duel.table_ruleset, seed=duel.seed), [])
            key = ('fantastic' if record['parameters']['fantastic_success'] else
                   'hit' if record['parameters']['success'] else 'miss')
            seen.add(key)
            self.assertEqual(record['impact']['target_prone'], key == 'fantastic')
            if key == 'miss':
                self.assertEqual(record['parameters']['attacker_faces'], [])
                self.assertEqual(record['impact']['target_damage'], 0)
        self.assertEqual(seen, {'hit', 'miss', 'fantastic'})

    def test_unsupported_shield_or_riposte_fail_before_damage(self):
        shielded = replace(self.attacker, weapons=frozenset({'shield'}), shield_active=True)
        riposte = replace(self.defender, powers=frozenset({'riposte'}))
        target_shield = replace(self.defender, weapons=frozenset({'shield'}))
        for attacker, defender in ((shielded, self.defender), (self.attacker, riposte),
                                   (self.attacker, target_shield)):
            with self.subTest(attacker=attacker.name, riposte='riposte' in defender.powers):
                duel, checkpoint = self.checkpoint(attacker=attacker, defender=defender)
                self.assertEqual(checkpoint['status'], 'opportunity')
                before = [(f.health, f.reactions) for f in duel.fighters]
                with self.assertRaisesRegex(IllegalAction, 'not supported'):
                    duel.resolve_bare_ram()
                self.assertEqual(before, [(f.health, f.reactions) for f in duel.fighters])

    def test_unsupported_heroic_floor_fails_without_health_or_reaction_change(self):
        attacker = replace(self.attacker, heroic=True)
        defender = replace(self.defender, max_health=1)
        duel, checkpoint = self.checkpoint(seed=1, attacker=attacker, defender=defender)
        self.assertEqual(checkpoint['status'], 'opportunity')
        before = [(fighter.health, fighter.reactions) for fighter in duel.fighters]
        with self.assertRaisesRegex(IllegalAction, 'Heroic damage floor'):
            duel.resolve_bare_ram()
        self.assertEqual(before, [(fighter.health, fighter.reactions) for fighter in duel.fighters])

    def test_fights_without_opportunity_end_without_ram(self):
        duel, result = self.checkpoint(distance=1)
        self.assertEqual(result['status'], 'no_opportunity')
        with self.assertRaises(IllegalAction):
            duel.resolve_bare_ram()

    def test_experimental_checkpoint_cannot_be_a_certified_runner(self):
        self.assertNotEqual(RamCheckpointDuel.execution_scope, 'two_character_physical')
        with self.assertRaisesRegex(RuntimeError, 'experimental engine'):
            _require_engine_ruleset(RamCheckpointDuel, RamCheckpointDuel.table_ruleset, None)
        duel, _ = self.checkpoint()
        with self.assertRaisesRegex(IllegalAction, 'cannot run a full Ram duel'):
            duel.run()
        unknown = replace(self.defender, powers=frozenset({'unimplemented_power'}))
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            self.checkpoint(defender=unknown)
        with self.assertRaisesRegex(ValueError, 'two distinct'):
            self.checkpoint(defender=replace(self.defender, name=self.attacker.name))

    def test_requires_trace_and_unchanged_checkpoint_state(self):
        with self.assertRaisesRegex(ValueError, 'complete trace'):
            RamCheckpointDuel((self.attacker, self.defender), self.policies,
                              seed=1, initial_distance=10, ram_actor=0)
        duel, _ = self.checkpoint()
        duel.fighters[0].health -= 1
        with self.assertRaisesRegex(IllegalAction, 'state changed'):
            duel.resolve_bare_ram()
        duel, _ = self.checkpoint()
        duel.damage_rng.random()
        with self.assertRaisesRegex(IllegalAction, 'state changed'):
            duel.resolve_bare_ram()
        duel, _ = self.checkpoint()
        duel.fighters[0].profile = replace(duel.fighters[0].profile, melee_bonus=1)
        with self.assertRaisesRegex(IllegalAction, 'state changed'):
            duel.resolve_bare_ram()

    def test_independent_checkpoint_audit_rejects_forgery(self):
        duel, _ = self.checkpoint(seed=3)
        log = list(duel.resolve_bare_ram()['log'])
        mutations = [('scope', 'full combat'), ('actor', 'Alvo'), ('target', 'Atacante'),
                     ('seq', 999), ('rules', ['ACT-01'])]
        for key, value in mutations:
            forged = deepcopy(log)
            forged[-1][key] = value
            with self.subTest(key=key):
                self.assertTrue(audit_ram_checkpoint(forged, (self.attacker, self.defender),
                                                     initial_distance=10, ruleset=duel.table_ruleset, seed=duel.seed))
        for section, key, value in [('before', 'reactions', 9), ('parameters', 'self_pool', 'shared'),
                                    ('impact', 'target_damage', 999), ('check', 'modifier', 77)]:
            forged = deepcopy(log)
            forged[-1]['transaction'][section][key] = value
            with self.subTest(section=section, key=key):
                self.assertTrue(audit_ram_checkpoint(forged, (self.attacker, self.defender),
                                                     initial_distance=10, ruleset=duel.table_ruleset, seed=duel.seed))
        self.assertTrue(audit_ram_checkpoint(log[:-1], (self.attacker, self.defender),
                                             initial_distance=10, ruleset=duel.table_ruleset, seed=duel.seed))
        self.assertTrue(audit_ram_checkpoint(log, (self.attacker, self.defender),
                                             initial_distance=10, ruleset=duel.table_ruleset, seed=duel.seed + 1))
        self.assertTrue(audit_ram_checkpoint([None], (self.attacker, self.defender),
                                             initial_distance=10, ruleset=duel.table_ruleset, seed=duel.seed))

    def test_victor_sheet_resolves_bare_ram_at_a_real_opportunity(self):
        hero, policies, scenarios = holdout_configurations(tuple(path.read_bytes() for path in INPUTS))
        foe, foe_policy, distance, _ = scenarios['gunner_open']
        profiles = (compile_duel(hero), compile_duel(foe))
        duel = RamCheckpointDuel(profiles, (policies['hammer_fast_hammer'], foe_policy),
                                 seed=987654, initial_distance=distance, max_rounds=30,
                                 audit=True, action_registry=DEFAULT_ACTIONS, ram_actor=0)
        self.assertEqual(duel.run_to_opportunity()['status'], 'opportunity')
        resolved = duel.resolve_bare_ram()
        self.assertEqual(audit_ram_checkpoint(resolved['log'], profiles, initial_distance=distance,
                                              ruleset=duel.table_ruleset, seed=duel.seed), [])
        record = resolved['transaction']
        self.assertEqual((record['parameters']['full_dice'], record['parameters']['ability']), (6, 6))
        self.assertEqual((record['parameters']['attacker_reduction'], record['parameters']['target_reduction']), (1, 0))
        self.assertEqual(record['parameters']['self_pool'], 'separate')
