from dataclasses import replace
from copy import deepcopy
import unittest

from blacklight.engine import Action, Profile, blacklight_profile
from combatants.actions import DEFAULT_ACTIONS
from combatants.split_fast import FastAction
from experimental.parry_duel import ParryDuel, ParryPolicy
from experimental.parry_audit import audit_parry_duel
from experimental.smg_duel import SubmachineDuel
from blacklight.audit import audit_profiled_log
from blacklight.split_audit import audit_split_fast
from tests.test_double_tap_duel import FixedDice


def fixture(*, victim=None, defender=None, focus=None):
    attacker = victim or Profile('Attacker', 3, 150, 90, 0, 1, 5, 2, 10, 11, 5)
    defender = defender or Profile('Defender', 3, 300, 90, 4, 5, 3, 2, 14, 15, 6,
                    ranged_range=10, ranged_bonus=2, ranged_is_ammunition=True,
                    powers=frozenset({'accuracy', 'point_blank_parry', 'fast_hands'}))
    policies = (ParryPolicy('attacker', use_ram=False, edge_mode='decline'),
                ParryPolicy('defender', use_ram=False))
    duel = ParryDuel((attacker, defender), policies, initial_prone=(False, False),
                     seed=1, initial_distance=1, max_rounds=3, audit=True,
                     ranged_weapons=('generic', 'submachine_gun'), action_registry=DEFAULT_ACTIONS)
    duel.round = 1
    duel._reset_reactions_for_round()
    duel.active_actor = 0
    duel.fighters[0].standard_available = True
    if focus is not None:
        duel.fighters[1].focus = focus
    return duel


class ParryDuelTests(unittest.TestCase):
    def test_miss_triggers_ranged_parry_fast_hands_focus_and_bleeding(self):
        duel = fixture()
        duel.rng = FixedDice((2, 2, 2, 6, 1, 6))
        duel.damage_rng = FixedDice((3,) * 30)
        duel._act(0, Action('melee'))
        attacks = [e for e in duel.log if e['type'] == 'attack']
        self.assertEqual(len(attacks), 2)
        self.assertFalse(attacks[0]['success'])
        self.assertTrue(attacks[1]['reaction'])
        self.assertEqual(attacks[1]['reaction_power'], 'point_blank_parry')
        self.assertTrue(attacks[1]['fantastic'])
        self.assertEqual(attacks[1]['troubles'], 1)  # SMG at close range
        self.assertEqual((duel.fighters[1].focus, duel.fighters[1].reactions,
                          duel.fast_hands_remaining[1]), (85, 1, 0))
        self.assertEqual(duel.fighters[0].bleeding, 5)

    def test_focus_floor_disables_parry(self):
        for focus, expected_attacks in ((5, 1), (6, 2)):
            duel = fixture(focus=focus)
            duel.rng = FixedDice((2, 2, 2, 6, 1, 6))
            duel.damage_rng = FixedDice((3,) * 30)
            duel._act(0, Action('melee'))
            self.assertEqual(sum(e['type'] == 'attack' for e in duel.log), expected_attacks)
            self.assertEqual(duel.fighters[1].focus, 5 if focus == 5 else 1)

    def test_fast_strikes_resolve_both_limbs_and_stun_before_reaction(self):
        victor = blacklight_profile()
        duel = fixture(victim=victor)
        duel.rng = FixedDice((2, 2, 2, 6, 1, 6))
        duel.damage_rng = FixedDice((3,) * 100)
        duel._act(0, FastAction('blade_fast', offhand='hammer', effect_limb=1))
        events = duel.log
        self.assertEqual(sum(e['type'] == 'fast_limb_check' for e in events), 2)
        self.assertTrue(any(e['type'] == 'condition_start' and e.get('condition') == 'stunned' for e in events))
        self.assertFalse(any(e['type'] == 'parry_start' for e in events))
        self.assertEqual((duel.fighters[1].focus, duel.fast_hands_remaining[1]), (90, 1))

    def test_two_failed_fast_limbs_allow_two_separate_reactions_after_both_effects(self):
        victor = replace(blacklight_profile(), max_health=500)
        duel = fixture(victim=victor)
        duel.rng = FixedDice((2, 2, 2, 2, 2, 2, 6, 1, 6, 6, 1, 6))
        duel.damage_rng = FixedDice((3,) * 100)
        duel._act(0, FastAction('blade_fast', offhand='hammer', effect_limb=1))
        events = duel.log
        fast_end = next(e['seq'] for e in events if e['type'] == 'fast_use_end')
        parries = [e for e in events if e['type'] == 'parry_start']
        self.assertEqual(len(parries), 2)
        self.assertTrue(all(event['seq'] > fast_end for event in parries))
        self.assertEqual(len({event['source_trigger'] for event in parries}), 2)
        self.assertEqual((duel.fighters[1].focus, duel.fighters[1].reactions,
                          duel.fast_hands_remaining[1]), (80, 0, 0))
        self.assertEqual(duel.fighters[0].bleeding, 5)
        early = list(deepcopy(events))
        index = next(i for i, event in enumerate(early) if event['type'] == 'fast_limb_start')
        nearby = early[index]
        early.insert(index, {'type': 'reaction_spent', 'actor': 'Defender', 'trigger': 1,
                             'remaining': 1, 'rules': ['CORE-P112-PARRY'],
                             'round': nearby['round'], 'bonus_round': nearby['bonus_round']})
        for seq, event in enumerate(early, 1):
            event['seq'] = seq
        self.assertTrue(any('Point-Blank Parry before' in issue for issue in audit_split_fast(early)))

    def test_parry_respects_brawling_and_ammunition_shield(self):
        victor = blacklight_profile()
        duel = fixture(victim=victor)
        duel.policies = (replace(duel.policies[0], shield_react=True), duel.policies[1])
        duel.rng = FixedDice((2, 2, 2, 6, 1, 6))
        duel.damage_rng = FixedDice((3,) * 100)
        duel._act(0, Action('melee'))
        attack = next(e for e in duel.log if e.get('reaction_power') == 'point_blank_parry')
        self.assertEqual(attack['target_number'], victor.melee_defense)
        self.assertTrue(attack['ammunition_immunity'])
        self.assertEqual((attack['damage'], duel.fighters[0].bleeding), (0, 0))

    def test_unsupported_prerequisites_and_policies_are_rejected(self):
        for powers in ({'fast_hands'}, {'point_blank_parry', 'fast_hands'}):
            duel = fixture()
            profile = replace(duel.fighters[1].profile, rank=2 if len(powers) > 1 else 3,
                              powers=frozenset(powers))
            with self.assertRaises(ValueError):
                fixture(defender=profile)

    def test_riposte_cannot_answer_a_missed_ranged_attack(self):
        attacker = Profile('Attacker', 3, 150, 90, 0, 1, 5, 2, 10, 11, 5, ranged_range=10)
        original = fixture().fighters[1].profile
        defender = replace(original, powers=original.powers | {'riposte'})
        duel = fixture(victim=attacker, defender=defender)
        duel.policies = (duel.policies[0], replace(duel.policies[1], prefer_parry=False))
        duel.rng = FixedDice((2, 2, 2))
        duel.damage_rng = FixedDice((3,) * 30)
        duel._act(0, Action('ranged'))
        self.assertEqual(sum(event['type'] == 'attack' for event in duel.log), 1)
        self.assertFalse(any(event['type'] == 'reaction_spent' for event in duel.log))

    def test_slow_dodge_and_parry_cannot_react_to_the_same_missed_attack(self):
        attacker = Profile('Attacker', 3, 150, 90, 0, 1, 5, 2, 10, 11, 5, ranged_range=10)
        original = fixture().fighters[1].profile
        defender = replace(original, powers=original.powers | {'slow_motion_dodge'})
        duel = fixture(victim=attacker, defender=defender)
        duel.rng = FixedDice((1, 2, 1, 1))
        duel.damage_rng = FixedDice((3,) * 30)
        duel._act(0, Action('ranged'))
        self.assertTrue(any(event['type'] == 'slow_motion_dodge' for event in duel.log))
        self.assertFalse(any(event['type'] == 'parry_start' for event in duel.log))
        self.assertEqual((duel.fighters[1].reactions, duel.fast_hands_remaining[1]), (0, 1))

    def test_no_new_powers_replays_previous_duel_exactly(self):
        duel = fixture()
        profiles = (duel.fighters[0].profile,
                    replace(duel.fighters[1].profile, powers=frozenset({'accuracy'})))
        policies = tuple(duel.policies)
        args = dict(initial_prone=(False, False), initial_distance=1, max_rounds=3,
                    audit=True, ranged_weapons=('generic', 'submachine_gun'),
                    action_registry=DEFAULT_ACTIONS)
        for seed in range(15):
            self.assertEqual(ParryDuel(profiles, policies, seed=seed, **args).run(),
                             SubmachineDuel(profiles, policies, seed=seed, **args).run())
        profiles = (blacklight_profile(), replace(profiles[1], heroic=True,
                                                   powers=profiles[1].powers | {'riposte'}))
        for seed in range(15):
            self.assertEqual(ParryDuel(profiles, policies, seed=seed, **args).run(),
                             SubmachineDuel(profiles, policies, seed=seed, **args).run())

    def test_full_duels_audit_parry_fast_strikes_and_shield(self):
        duel = fixture(victim=blacklight_profile())
        profiles = tuple(f.profile for f in duel.fighters)
        policies = (replace(duel.policies[0], weapon='hammer', offhand='blade', prefer_fast=True,
                            effect_limb=1, shield_react=True), duel.policies[1])
        observed = set()
        for seed in range(80):
            args = dict(initial_prone=(False, False), initial_distance=1, max_rounds=5, audit=True,
                        ranged_weapons=('generic', 'submachine_gun'), action_registry=DEFAULT_ACTIONS)
            result = ParryDuel(profiles, policies, seed=seed, **args).run()
            self.assertEqual(audit_parry_duel(result, profiles, ranged_weapons=args['ranged_weapons'],
                             initial_prone=(False, False), initial_distance=1, expected_seed=seed,
                             max_rounds=5, ruleset=ParryDuel.table_ruleset), [])
            for event in result.log:
                if event['type'] in ('parry_start', 'fast_use_start', 'shield_activate'):
                    observed.add(event['type'])
        self.assertEqual(observed, {'parry_start', 'fast_use_start', 'shield_activate'})

    def test_auditor_rejects_forged_cost_pool_and_damage_attribution(self):
        duel = fixture()
        profiles, policies = tuple(f.profile for f in duel.fighters), tuple(duel.policies)
        result = ParryDuel(profiles, policies, seed=0, initial_prone=(False, False), initial_distance=1,
                           max_rounds=3, audit=True, ranged_weapons=('generic', 'submachine_gun'),
                           action_registry=DEFAULT_ACTIONS).run()
        context = dict(ranged_weapons=('generic', 'submachine_gun'), initial_prone=(False, False),
                       initial_distance=1, expected_seed=0, max_rounds=3, ruleset=ParryDuel.table_ruleset)
        self.assertEqual(audit_parry_duel(result, profiles, **context), [])
        self.assertTrue(audit_profiled_log(result.log, profiles, ruleset=ParryDuel.table_ruleset))
        for event_type, field, value in (('reaction_spent', 'pool', 'ordinary'),
                                         ('focus_spent', 'amount', 4),
                                         ('parry_end', 'source_trigger', 999),
                                         ('fast_hands_reset', 'reactions', 2),
                                         ('reaction_considered', 'trigger', 999),
                                         ('reaction_queued', 'trigger', [])):
            log = deepcopy(result.log)
            index = next(i for i, event in enumerate(log) if event['type'] == event_type
                         and (event_type != 'reaction_spent' or event.get('source') == 'point_blank_parry'))
            log[index][field] = value
            self.assertTrue(audit_parry_duel(replace(result, log=log), profiles, **context))

    def test_nested_parries_use_distinct_reactions_and_both_pools(self):
        defender = fixture().fighters[1].profile
        profiles = (replace(defender, name='A', max_health=600),
                    replace(defender, name='B', max_health=600))
        policies = (ParryPolicy('A', use_ram=False), ParryPolicy('B', use_ram=False))
        weapons = ('submachine_gun', 'submachine_gun')
        args = dict(seed=0, initial_prone=(False, False), initial_distance=1,
                    max_rounds=8, audit=True, ranged_weapons=weapons, action_registry=DEFAULT_ACTIONS)
        result = ParryDuel(profiles, policies, **args).run()
        self.assertEqual(result, ParryDuel(profiles, policies, **args).run())
        self.assertEqual(audit_parry_duel(result, profiles, ranged_weapons=weapons,
                         initial_prone=(False, False), initial_distance=1, expected_seed=0,
                         max_rounds=8, ruleset=ParryDuel.table_ruleset), [])
        parry_misses = {event['trigger'] for event in result.log if event['type'] == 'attack'
                        and event.get('reaction_power') == 'point_blank_parry' and not event['success']}
        self.assertTrue(any(event['type'] == 'parry_start' and event['source_trigger'] in parry_misses
                            for event in result.log))
        pools = {}
        for event in result.log:
            if event['type'] == 'reaction_spent' and event.get('source') == 'point_blank_parry':
                pools.setdefault((event['actor'], event['round'], event['bonus_round']), set()).add(event['pool'])
        self.assertTrue(any(used == {'ordinary', 'fast_hands'} for used in pools.values()))

    def test_slow_dodge_and_restricted_reactions_audit_together(self):
        defender = fixture().fighters[1].profile
        defender = replace(defender, powers=defender.powers | {'slow_motion_dodge'}, max_health=600)
        profiles = (replace(defender, name='A'), replace(defender, name='B'))
        policies = (ParryPolicy('A', use_ram=False), ParryPolicy('B', use_ram=False))
        weapons = ('submachine_gun', 'submachine_gun')
        for seed in range(30):
            result = ParryDuel(profiles, policies, seed=seed, initial_prone=(False, False),
                               initial_distance=1, max_rounds=4, audit=True,
                               ranged_weapons=weapons, action_registry=DEFAULT_ACTIONS).run()
            self.assertEqual(audit_parry_duel(result, profiles, ranged_weapons=weapons,
                             initial_prone=(False, False), initial_distance=1, expected_seed=seed,
                             max_rounds=4, ruleset=ParryDuel.table_ruleset), [])
