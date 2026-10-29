from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from blacklight.engine import ReactionEvent
from combatants.actions import DEFAULT_ACTIONS
from experimental.entangled_reaction_audit import audit_entangled_reactions
from experimental.entangled_reaction_duel import EntangledReactionDuel, EntangledReactionPolicy
from tests import test_entangled_attack_duel as fixtures
from scripts.entangled_reaction_demo import run as run_demo


class EntangledReactionDuelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.EntangledAttackDuelTests.setUpClass()
        cls.profiles = fixtures.EntangledAttackDuelTests.profiles
        cls.weapons = fixtures.EntangledAttackDuelTests.weapons

    def policies(self, *, synthetic=False):
        return (EntangledReactionPolicy('crossbones', prefer_grapple=True, prefer_stopping=True,
                    use_ram=False, attack_when_grabbing=True),
                EntangledReactionPolicy('victor', weapon='hammer', offhand='blade', prefer_fast=True,
                    effect_limb=int(synthetic), shield_react=True, use_ram=False,
                    escape_reaction=False, attack_when_grabbed=True))

    def run_case(self, seed, trouble, *, synthetic=False):
        profiles = self.profiles
        if synthetic:
            a, b = profiles
            profiles = (replace(a, max_health=500), replace(b, max_health=500, ranged_range=10,
                ranged_bonus=2, ranged_is_ammunition=True, powers=b.powers | {'point_blank_parry', 'fast_hands'}))
        rounds = 8 if synthetic else 4
        duel = EntangledReactionDuel(profiles, self.policies(synthetic=synthetic), seed=seed,
            initial_prone=(False, False), initial_distance=1, max_rounds=rounds, audit=True,
            action_registry=DEFAULT_ACTIONS, ranged_weapons=self.weapons, stop_on_attacker=profiles[1].name,
            declared_armed_lethal=(profiles[0].name,), escape_trigger_mode='attack',
            inside_attack_trouble=trouble)
        return duel, duel.run(), profiles

    def audit_case(self, result, profiles, seed, trouble, *, synthetic=False):
        return audit_entangled_reactions(result, profiles, inside_attack_trouble=trouble,
            declared_armed_lethal=(profiles[0].name,), escape_trigger_mode='attack',
            ranged_weapons=self.weapons, initial_prone=(False, False), initial_distance=1,
            expected_seed=seed, max_rounds=8 if synthetic else 4, ruleset='split_fast_v3',
            self_damage_mode='stop_before_heal_reject_lethal', stop_on_attacker=profiles[1].name)

    def test_replayed_duels_with_both_reaction_types_and_trouble_hypotheses(self):
        witnessed = set()
        for trouble in (False, True):
            for seed in range(60):
                with self.subTest(trouble=trouble, seed=seed):
                    _, result, profiles = self.run_case(seed, trouble)
                    self.assertEqual(result, self.run_case(seed, trouble)[1])
                    self.assertEqual(self.audit_case(result, profiles, seed, trouble), [])
                    held = False
                    for event in result.log:
                        if event['type'] == 'grapple_end' and event['transaction']['attack_success']:
                            held = True
                        elif event['type'] == 'grapple_escape' and event['transaction']['success']:
                            held = False
                        elif event['type'] == 'grapple_release':
                            held = False
                        elif held and event['type'] == 'attack' and event.get('reaction'):
                            witnessed.add('parry' if event.get('reaction_power') == 'point_blank_parry' else 'riposte')
        self.assertEqual(witnessed, {'parry', 'riposte'})

    def test_nested_reaction_interrupts_pending_fast_strike_reaction(self):
        # Explicitly synthetic: Victor is given Point-Blank Parry/Fast Hands.
        _, result, profiles = self.run_case(142, True, synthetic=True)
        self.assertEqual(self.audit_case(result, profiles, 142, True, synthetic=True), [])
        events = list(result.log)
        dequeued = [(i, e['trigger']) for i, e in enumerate(events) if e['type'] == 'entangled_reaction_dequeued']
        nested = next(i for i, trigger in dequeued if trigger == 19)
        older = next(i for i, trigger in dequeued if trigger == 17)
        self.assertLess(nested, older)
        checks = [next(i for i, e in enumerate(events) if e['type'] == 'fast_limb_check'
                       and e['trigger'] == trigger) for trigger in (16, 17)]
        attacks = [next(i for i, e in enumerate(events) if e['type'] == 'attack'
                        and e['trigger'] == trigger) for trigger in (16, 17)]
        end = next(i for i, e in enumerate(events) if e['type'] == 'fast_use_end' and i > attacks[1])
        first_reaction = next(i for i, trigger in dequeued if trigger == 16)
        self.assertLess(max(checks), min(attacks))
        self.assertLess(max(attacks), end)
        self.assertLess(end, first_reaction)
        self.assertLess(first_reaction, nested)
        rows = deepcopy(events)
        rows[nested]['trigger'], rows[older]['trigger'] = rows[older]['trigger'], rows[nested]['trigger']
        self.assertTrue(self.audit_case(replace(result, log=tuple(rows)), profiles, 142, True, synthetic=True))

    def test_incapacitated_attack_source_cannot_receive_a_queued_counterattack(self):
        duel, _, _ = self.run_case(11, True)
        duel.fighters[0].health = 0
        self.assertFalse(duel._reaction_source_available(ReactionEvent('riposte', 1, 0, 101)))

    def test_spurious_ranged_attack_and_dequeue_are_detected(self):
        _, result, profiles = self.run_case(11, True)
        rows = deepcopy(list(result.log))
        index = next(i for i, e in enumerate(rows) if e['type'] == 'entangled_reaction_dequeued')
        rows[index]['trigger'] += 100
        self.assertTrue(self.audit_case(replace(result, log=tuple(rows)), profiles, 11, True))
        rows = deepcopy(list(result.log))
        index = next(i for i, e in enumerate(rows) if e.get('reaction_power') == 'point_blank_parry'
                     and e['type'] == 'attack' and any(x['type'] == 'entangled_attack_check'
                     and x['trigger'] == e['trigger'] for x in rows))
        rows[index]['reaction_power'] = 'other'
        self.assertTrue(self.audit_case(replace(result, log=tuple(rows)), profiles, 11, True))

    def test_parry_combines_entanglement_and_gun_trouble_and_respects_shield(self):
        _, result, profiles = self.run_case(11, True)
        parry = next(e for e in result.log if e.get('type') == 'attack'
                     and e.get('reaction_power') == 'point_blank_parry'
                     and any(x['type'] == 'entangled_attack_check' and x['trigger'] == e['trigger']
                             for x in result.log))
        self.assertEqual((parry['troubles'], parry['ammunition_immunity'], parry['damage']), (2, True, 0))
        self.assertEqual(self.audit_case(result, profiles, 11, True), [])

    def test_synthetic_pinned_parry_combines_slow_motion_dodge(self):
        _, result, profiles = self.run_case(1, True, synthetic=True)
        marker = next(e for e in result.log if e.get('type') == 'entangled_attack_check'
                      and e.get('mode') == 'ranged' and e.get('pinned'))
        attack = next(e for e in result.log if e.get('type') == 'attack'
                      and e.get('trigger') == marker['trigger'])
        self.assertEqual((marker['added_troubles'], attack['troubles']), (2, 3))
        self.assertTrue(any(e.get('type') == 'slow_motion_dodge' and e.get('trigger') == marker['trigger']
                            for e in result.log))
        self.assertEqual(self.audit_case(result, profiles, 1, True, synthetic=True), [])

    def test_demonstration_is_audited_and_never_overwrites(self):
        with TemporaryDirectory() as directory, patch('scripts.entangled_reaction_demo.source_commit', return_value='test'):
            output = Path(directory) / 'demo.json'
            run_demo(output)
            contents = output.read_bytes()
            data = json.loads(contents)
            self.assertEqual(data['audit_issues'], [])
            self.assertIn('Banging Heads', data['crossbones_subset']['omitted_powers'])
            self.assertEqual(data['victor_sheet']['name'], 'Blacklight')
            with self.assertRaises((FileExistsError, ValueError)):
                run_demo(output)
            self.assertEqual(output.read_bytes(), contents)
