from dataclasses import asdict, replace
from copy import deepcopy
import unittest

from blacklight.engine import IllegalAction, Move, Profile
from combatants.actions import DEFAULT_ACTIONS
from combatants.duel_adapter import compile_duel
from combatants.runner import _require_engine_ruleset
from experimental.prone_duel import ProneDuel, PronePolicy
from experimental.prone_duel_audit import audit_prone_log
from experimental.ram_prone_duel import RamProneDuel, RamPronePolicy
from experimental.ram_prone_audit import audit_ram_prone_duel
from scripts.current_study_holdout import INPUTS, holdout_configurations


class StationaryRamPolicy(RamPronePolicy):
    def choose_move(self, observation):
        return Move()


def profile(name, melee=4, *, health=100, dr=0, initiative=0, **kwargs):
    return Profile(name, 3, health, 60, melee, 0, 5, 2, 10 + melee, 10, 5,
                   health_dr=dr, initiative_modifier=initiative, **kwargs)


class RamProneDuelTests(unittest.TestCase):
    def test_victor_can_complete_duel_after_ram(self):
        hero, choices, scenarios = holdout_configurations(tuple(path.read_bytes() for path in INPUTS))
        foe, foe_policy, distance, _ = scenarios['gunner_open']
        profiles = (compile_duel(hero), compile_duel(foe))
        policies = (RamPronePolicy(**asdict(choices['hammer_fast_hammer'])),
                    RamPronePolicy(**asdict(foe_policy), use_ram=False))
        duel = RamProneDuel(profiles, policies, initial_prone=(False, False), seed=987654,
                            initial_distance=distance, max_rounds=30, audit=True,
                            action_registry=DEFAULT_ACTIONS)
        result = duel.run()
        attacks = [event for event in result.log if event['type'] == 'ram_attack']
        self.assertGreaterEqual(len(attacks), 1)
        self.assertEqual(attacks[0]['transaction']['parameters']['self_pool'], 'separate')
        self.assertEqual((attacks[0]['target_damage_applied'], attacks[0]['attacker_damage_applied']), (66, 27))
        self.assertTrue(any(event['type'] == 'turn_end' for event in result.log[result.log.index(attacks[0]) + 1:]))
        self.assertEqual(audit_prone_log(result.log, profiles, initial_prone=(False, False),
                                         initial_distance=distance), [])
        self.assertEqual(audit_ram_prone_duel(result, profiles, initial_prone=(False, False),
                                              initial_distance=distance, expected_seed=987654,
                                              max_rounds=30, ruleset=duel.table_ruleset), [])
        replay = RamProneDuel(profiles, policies, initial_prone=(False, False), seed=987654,
                              initial_distance=distance, max_rounds=30, audit=True,
                              action_registry=DEFAULT_ACTIONS).run()
        self.assertEqual(replay, result)

    def test_declining_ram_leaves_prone_duel_replay_unchanged(self):
        profiles = (profile('A', initiative=100), profile('B'))
        base = (PronePolicy('A', knockback_stance=False), PronePolicy('B', knockback_stance=False))
        experimental = tuple(RamPronePolicy(**asdict(policy), use_ram=False) for policy in base)
        for seed in range(15):
            baseline = ProneDuel(profiles, base, initial_prone=(False, False), seed=seed,
                                 initial_distance=10, max_rounds=5, audit=True,
                                 action_registry=DEFAULT_ACTIONS).run()
            result = RamProneDuel(profiles, experimental, initial_prone=(False, False), seed=seed,
                                  initial_distance=10, max_rounds=5, audit=True,
                                  action_registry=DEFAULT_ACTIONS).run()
            for field in ('outcome', 'winner', 'final_health', 'final_focus', 'metrics', 'turns', 'rounds'):
                self.assertEqual(getattr(result, field), getattr(baseline, field))
            clean = lambda events: [{key: value for key, value in event.items() if key != 'seq'}
                                    for event in events if event['type'] not in ('ram_opportunity', 'ram_declined')]
            self.assertEqual(clean(result.log), clean(baseline.log))

    def test_active_target_shield_stacks_with_sturdy(self):
        profiles = (profile('A', initiative=100),
                    profile('B', dr=1, weapons=frozenset({'shield'}), shield_active=True))
        policies = (RamPronePolicy('A', knockback_stance=False),
                    StationaryRamPolicy('B', always_wait=True, use_ram=False))
        duel = RamProneDuel(profiles, policies, initial_prone=(False, False), seed=1,
                            initial_distance=10, max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
        result = duel.run()
        attack = next(event for event in result.log if event['type'] == 'ram_attack')
        self.assertEqual(attack['transaction']['parameters']['target_reduction'], 3)

    def test_audited_ram_hits_misses_prone_shield_and_riposte(self):
        profiles = (profile('A', health=250, initiative=100),
                    profile('B', health=250, dr=1, powers=frozenset({'riposte'}),
                            weapons=frozenset({'shield'})))
        policies = (RamPronePolicy('A', knockback_stance=False),
                    StationaryRamPolicy('B', always_wait=True, use_ram=False, riposte=True,
                                        shield_react=True, stand_when_prone=False))
        observed = set()
        for seed in range(120):
            with self.subTest(seed=seed):
                duel = RamProneDuel(profiles, policies, initial_prone=(False, False), seed=seed,
                                    initial_distance=10, max_rounds=3, audit=True, action_registry=DEFAULT_ACTIONS)
                result = duel.run()
                self.assertEqual(audit_ram_prone_duel(result, profiles, initial_prone=(False, False),
                                                      initial_distance=10, expected_seed=seed,
                                                      max_rounds=3, ruleset=duel.table_ruleset), [])
                for event in result.log:
                    if event['type'] == 'ram_attack':
                        params = event['transaction']['parameters']
                        observed.add('fantastic' if params['fantastic_success'] else
                                     'hit' if params['success'] else 'miss')
                    if event['type'] in ('shield_activate', 'prone_start'):
                        observed.add(event['type'])
                    if event['type'] == 'attack' and event.get('reaction') is True:
                        observed.add('riposte')
        self.assertTrue({'hit', 'miss', 'fantastic', 'shield_activate', 'prone_start', 'riposte'} <= observed)

    def test_missed_ram_can_trigger_nested_ripostes_within_reaction_budgets(self):
        profiles = (profile('A', health=250, initiative=100, powers=frozenset({'riposte'}),
                            traits=frozenset({'combat_reflexes'})),
                    profile('B', health=250, powers=frozenset({'riposte'})))
        policies = (RamPronePolicy('A', riposte=True),
                    StationaryRamPolicy('B', always_wait=True, use_ram=False, riposte=True))
        found = False
        for seed in range(500):
            duel = RamProneDuel(profiles, policies, initial_prone=(False, False), seed=seed,
                                initial_distance=10, max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
            result = duel.run()
            if any(event.get('type') == 'attack' and event.get('reaction') is True and event.get('actor') == 'A'
                   for event in result.log):
                self.assertTrue(any(event['type'] == 'ram_attack' and not event['transaction']['parameters']['success']
                                    for event in result.log))
                self.assertTrue(any(event.get('type') == 'attack' and event.get('reaction') is True and
                                    event.get('actor') == 'B' for event in result.log))
                self.assertEqual(audit_ram_prone_duel(result, profiles, initial_prone=(False, False),
                                                      initial_distance=10, expected_seed=seed,
                                                      max_rounds=1, ruleset=duel.table_ruleset), [])
                found = True
                break
        self.assertTrue(found)

    def test_self_incapacitation_aborts_the_experimental_duel(self):
        profiles = (profile('A', health=1, initiative=100), profile('B'))
        policies = (RamPronePolicy('A'), StationaryRamPolicy('B', always_wait=True, use_ram=False))
        duel = RamProneDuel(profiles, policies, initial_prone=(False, False), seed=1,
                            initial_distance=10, max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
        with self.assertRaisesRegex(IllegalAction, 'self-incapacitation'):
            duel.run()
        self.assertFalse(any(event['type'] == 'ram_attack' for event in duel.log))

    def test_ram_is_declined_with_active_attacker_shield(self):
        profiles = (profile('A', health=250, initiative=100, weapons=frozenset({'shield'}),
                            shield_active=True), profile('B', health=250))
        policies = (RamPronePolicy('A'), StationaryRamPolicy('B', always_wait=True, use_ram=False))
        duel = RamProneDuel(profiles, policies, initial_prone=(False, False), seed=1,
                            initial_distance=10, max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
        result = duel.run()
        self.assertTrue(any(event['type'] == 'ram_declined' and event['actor'] == 'A' for event in result.log))
        self.assertFalse(any(event['type'] == 'ram_attack' and event['actor'] == 'A' for event in result.log))
        self.assertEqual(audit_ram_prone_duel(result, profiles, initial_prone=(False, False),
                                              initial_distance=10, expected_seed=1,
                                              max_rounds=1, ruleset=duel.table_ruleset), [])

    def test_unsupported_ram_attack_stance_aborts(self):
        profiles = (profile('A', health=250, initiative=100, powers=frozenset({'attack_stance'})),
                    profile('B', health=250))
        policies = (RamPronePolicy('A'), StationaryRamPolicy('B', always_wait=True, use_ram=False))
        duel = RamProneDuel(profiles, policies, initial_prone=(False, False), seed=1,
                            initial_distance=10, max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
        duel.fighters[0].stance = True
        with self.assertRaisesRegex(IllegalAction, 'Attack Stance'):
            duel.run()

    def test_armed_nonhero_ram_fails_closed_when_nonlethal_status_is_unclear(self):
        profiles = (profile('A', health=250, initiative=100, weapons=frozenset({'hammer'})),
                    profile('B', health=250))
        policies = (RamPronePolicy('A'), StationaryRamPolicy('B', always_wait=True, use_ram=False))
        duel = RamProneDuel(profiles, policies, initial_prone=(False, False), seed=1,
                            initial_distance=10, max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
        with self.assertRaisesRegex(IllegalAction, 'nonlethal Ram status'):
            duel.run()
        self.assertFalse(any(event['type'] == 'ram_attack' for event in duel.log))

    def test_initially_prone_attacker_cannot_count_standing_as_full_speed(self):
        profiles = (profile('A', health=250, initiative=100), profile('B', health=250))
        policies = (RamPronePolicy('A'), StationaryRamPolicy('B', always_wait=True, use_ram=False))
        duel = RamProneDuel(profiles, policies, initial_prone=(True, False), seed=1,
                            initial_distance=10, max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
        result = duel.run()
        self.assertTrue(any(event['type'] == 'prone_stand' and event['actor'] == 'A' for event in result.log))
        self.assertFalse(any(event['type'] == 'ram_attack' and event['actor'] == 'A' for event in result.log))
        self.assertEqual(audit_ram_prone_duel(result, profiles, initial_prone=(True, False),
                                              initial_distance=10, expected_seed=1,
                                              max_rounds=1, ruleset=duel.table_ruleset), [])

    def test_already_prone_target_gives_ram_one_edge(self):
        profiles = (profile('A', health=250, initiative=100), profile('B', health=250))
        policies = (RamPronePolicy('A'), StationaryRamPolicy('B', always_wait=True, use_ram=False,
                                                             stand_when_prone=False))
        duel = RamProneDuel(profiles, policies, initial_prone=(False, True), seed=1,
                            initial_distance=10, max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
        result = duel.run()
        attack = next(event for event in result.log if event['type'] == 'ram_attack')
        self.assertEqual((attack['edges'], attack['troubles']), (1, 0))
        self.assertEqual(audit_ram_prone_duel(result, profiles, initial_prone=(False, True),
                                              initial_distance=10, expected_seed=1,
                                              max_rounds=1, ruleset=duel.table_ruleset), [])

    def test_bare_ram_target_is_nonlethal_even_without_heroic_tag(self):
        for heroic in (False, True):
            with self.subTest(heroic=heroic):
                profiles = (profile('A', health=250, initiative=100, heroic=heroic), profile('B', health=1))
                policies = (RamPronePolicy('A'), StationaryRamPolicy('B', always_wait=True, use_ram=False))
                duel = RamProneDuel(profiles, policies, initial_prone=(False, False), seed=1,
                                    initial_distance=10, max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
                result = duel.run()
                attack = next(event for event in result.log if event['type'] == 'ram_attack')
                self.assertLess(attack['transaction']['after']['target_health'], 0)
                self.assertEqual(attack['target_health_after'], 0)
                self.assertEqual(attack['target_damage_applied'], 1)
                self.assertEqual(audit_ram_prone_duel(result, profiles, initial_prone=(False, False),
                                                      initial_distance=10, expected_seed=1,
                                                      max_rounds=1, ruleset=duel.table_ruleset), [])

    def test_prone_target_can_stand_on_following_turn_after_fantastic_ram(self):
        profiles = (profile('A', health=250, initiative=100), profile('B', health=250))
        policies = (RamPronePolicy('A'), StationaryRamPolicy('B', always_wait=True, use_ram=False))
        found = False
        for seed in range(80):
            duel = RamProneDuel(profiles, policies, initial_prone=(False, False), seed=seed,
                                initial_distance=10, max_rounds=2, audit=True, action_registry=DEFAULT_ACTIONS)
            result = duel.run()
            if any(event['type'] == 'prone_start' for event in result.log):
                self.assertTrue(any(event['type'] == 'prone_stand' and event['actor'] == 'B'
                                    for event in result.log))
                self.assertEqual(audit_ram_prone_duel(result, profiles, initial_prone=(False, False),
                                                      initial_distance=10, expected_seed=seed,
                                                      max_rounds=2, ruleset=duel.table_ruleset), [])
                found = True
                break
        self.assertTrue(found)

    def test_fantastic_failure_does_not_apply_damage_or_prone(self):
        profiles = (profile('A', health=300, initiative=100),
                    profile('B', melee=100, health=300))
        policies = (RamPronePolicy('A'), StationaryRamPolicy('B', always_wait=True, use_ram=False))
        found = False
        for seed in range(80):
            duel = RamProneDuel(profiles, policies, initial_prone=(False, False), seed=seed,
                                initial_distance=10, max_rounds=1, audit=True, action_registry=DEFAULT_ACTIONS)
            result = duel.run()
            event = next(e for e in result.log if e['type'] == 'ram_attack')
            if event['transaction']['check']['fantastic_roll'] and not event['transaction']['parameters']['success']:
                self.assertEqual(event['target_damage_applied'], 0)
                self.assertEqual(event['attacker_damage_applied'], 0)
                self.assertFalse(any(e['type'] == 'prone_start' for e in result.log))
                self.assertEqual(audit_ram_prone_duel(result, profiles, initial_prone=(False, False),
                                                      initial_distance=10, expected_seed=seed,
                                                      max_rounds=1, ruleset=duel.table_ruleset), [])
                found = True
                break
        self.assertTrue(found)

    def test_experimental_host_cannot_use_certified_runner(self):
        with self.assertRaisesRegex(RuntimeError, 'experimental engine'):
            _require_engine_ruleset(RamProneDuel, RamProneDuel.table_ruleset, None)
        with self.assertRaises(ValueError):
            RamPronePolicy('invalid', use_ram=1)

    def test_full_audit_rejects_forged_ram_and_summary(self):
        hero, choices, scenarios = holdout_configurations(tuple(path.read_bytes() for path in INPUTS))
        foe, foe_policy, distance, _ = scenarios['gunner_open']
        profiles = (compile_duel(hero), compile_duel(foe))
        policies = (RamPronePolicy(**asdict(choices['hammer_fast_hammer'])),
                    RamPronePolicy(**asdict(foe_policy), use_ram=False))
        duel = RamProneDuel(profiles, policies, initial_prone=(False, False), seed=987654,
                            initial_distance=distance, max_rounds=30, audit=True,
                            action_registry=DEFAULT_ACTIONS)
        result = duel.run()
        def audit(candidate):
            return audit_ram_prone_duel(candidate, profiles, initial_prone=(False, False),
                                        initial_distance=distance, expected_seed=987654,
                                        max_rounds=30, ruleset=duel.table_ruleset)
        self.assertEqual(audit(result), [])
        index = next(i for i, event in enumerate(result.log) if event['type'] == 'ram_attack')
        for key, value in (('target_damage_applied', 999), ('attacker_damage_applied', 0),
                           ('target_health_after', 999), ('target_damage_mitigated', True),
                           ('edges', True), ('scope', 'certified'), ('seq', 999)):
            with self.subTest(key=key):
                log = deepcopy(list(result.log))
                log[index][key] = value
                self.assertTrue(audit(replace(result, log=tuple(log))))
        for section, key, value in (('parameters', 'self_pool', 'shared'),
                                    ('before', 'reactions', 9), ('check', 'seed', 1),
                                    ('impact', 'target_damage', 999)):
            with self.subTest(section=section, key=key):
                log = deepcopy(list(result.log))
                log[index]['transaction'][section][key] = value
                self.assertTrue(audit(replace(result, log=tuple(log))))
        metrics = tuple(dict(row) for row in result.metrics)
        metrics[0]['attacks'] += 1
        self.assertTrue(audit(replace(result, metrics=metrics)))
        metrics = tuple(dict(row) for row in result.metrics)
        metrics[0]['attacks'] = True
        self.assertTrue(audit(replace(result, metrics=metrics)))
        log = deepcopy(list(result.log))
        log[index]['type'] = 'unsupported_effect'
        self.assertTrue(audit(replace(result, log=tuple(log))))
        log = deepcopy(list(result.log))
        marker = next(i for i, event in enumerate(log) if event['type'] == 'ram_opportunity')
        log.pop(marker)
        for i, event in enumerate(log, 1):
            event['seq'] = i
        self.assertTrue(audit(replace(result, log=tuple(log))))
