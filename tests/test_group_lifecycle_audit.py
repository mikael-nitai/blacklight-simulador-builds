"""Adversarial, manually specified controls for experimental group traces."""

from copy import deepcopy
from dataclasses import replace
from unittest import TestCase
from unittest.mock import patch

from blacklight.engine import Duel, Profile, blacklight_profile
from combatants.group import GroupBattle, GroupPolicy
from combatants.group_lifecycle_audit import audit_group_lifecycle


class FixedDice:
    def __init__(self, values):
        self.values = iter(values)

    def randint(self, low, high):
        value = next(self.values)
        if not low <= value <= high:
            raise AssertionError('Invalid forced face')
        return value


def renumber(rows):
    for index, row in enumerate(rows, 1):
        row['seq'] = index
    return rows


class TestGroupLifecycleAudit(TestCase):
    def test_overlapping_sources_expire_separately_without_stacking(self):
        hero = blacklight_profile()
        profiles = tuple(replace(hero, name=name) for name in ('A', 'B', 'C'))
        rows = []
        def emit(kind, **data):
            rows.append({'seq': len(rows) + 1, 'round': 1, 'bonus_round': False,
                         'type': kind, 'rules': [], **data})
        def begin(actor, count):
            emit('group_turn_boundary', actor=actor, turn_count=count)
            emit('turn_start', actor=actor)
        def end(actor):
            emit('turn_end', actor=actor)
        begin('A', 1)
        emit('condition_start', actor='C', condition='stunned', expires_on_actor='A',
             source_turn_count=2, instance='stunned:0:2')
        end('A')
        begin('B', 1)
        emit('condition_start', actor='C', condition='stunned', expires_on_actor='B',
             source_turn_count=2, instance='stunned:1:2')
        end('B')
        emit('group_turn_boundary', actor='A', turn_count=2)
        emit('condition_instance_end', actor='C', condition='stunned', expires_on_actor='A',
             instance='stunned:0:2')
        emit('turn_start', actor='A')
        end('A')
        emit('group_turn_boundary', actor='B', turn_count=2)
        emit('condition_instance_end', actor='C', condition='stunned', expires_on_actor='B',
             instance='stunned:1:2')
        emit('condition_end', actor='C', condition='stunned')
        emit('turn_start', actor='B')
        end('B')
        self.assertEqual(audit_group_lifecycle(rows, profiles), [])
        forged = deepcopy(rows)
        first_end = next(i for i, event in enumerate(forged) if event['type'] == 'condition_instance_end')
        forged.insert(first_end + 1, {'seq': 0, 'round': 1, 'bonus_round': False, 'rules': [],
                                      'type': 'condition_end', 'actor': 'C', 'condition': 'stunned'})
        self.assertTrue(any('without expiration of every instance' in issue
                            for issue in audit_group_lifecycle(renumber(forged), profiles)))

    def test_action_after_turn_end_is_rejected(self):
        hero = blacklight_profile()
        profiles = (hero, replace(hero, name='A'), replace(hero, name='B'))
        policy = GroupPolicy('wait', always_wait=True)
        battle = GroupBattle(profiles, (policy,) * 3, teams=('h', 'e', 'e'),
                             initiative_roles=('player', 'npc', 'npc'),
                             initiative_tie_order=(0, 1, 2), seed=91, max_rounds=2, audit=True)
        result = battle.run()
        self.assertEqual(audit_group_lifecycle(result.log, profiles), [])
        rows = deepcopy(list(result.log))
        wait = next(event for event in rows if event['type'] == 'wait')
        rows.remove(wait)
        index = next(i for i, event in enumerate(rows)
                     if event['type'] == 'turn_end' and event['actor'] == wait['actor'])
        rows.insert(index + 1, wait)
        self.assertTrue(any('outside an eligible actor turn' in issue
                            for issue in audit_group_lifecycle(renumber(rows), profiles)))

    def test_stun_deadline_and_omitted_expiration_are_rejected(self):
        hero = blacklight_profile()
        profiles = (hero, replace(hero, name='A'), replace(hero, name='B'))
        policies = tuple(GroupPolicy(name, weapon='hammer', prefer_fast=True, shield_react=True)
                         for name in ('h', 'a', 'b'))
        battle = GroupBattle(profiles, policies, teams=('h', 'e', 'e'),
                             initiative_roles=('player', 'npc', 'npc'),
                             initiative_tie_order=(0, 1, 2), seed=0, max_rounds=10, audit=True)
        result = battle.run()
        self.assertEqual(audit_group_lifecycle(result.log, profiles), [])
        rows = deepcopy(list(result.log))
        stun = next(row for row in rows if row['type'] == 'condition_start' and row['condition'] == 'stunned')
        stun['source_turn_count'] = 999
        self.assertTrue(any('Stunned source, identity or deadline' in issue
                            for issue in audit_group_lifecycle(rows, profiles)))
        rows = deepcopy(list(result.log))
        expiration = next(row for row in rows if row['type'] == 'condition_instance_end')
        rows.remove(expiration)
        self.assertTrue(any('expiration' in issue or 'Stunned ended' in issue
                            for issue in audit_group_lifecycle(renumber(rows), profiles)))

    def forced_battle(self, *, shields=False, fifo=False):
        hero = replace(blacklight_profile(), heroic=False)
        enemy = Profile('A', 3, 500, 90, 4, 2, 3, 2, 14, 12, 5,
                        powers=frozenset({'riposte'}),
                        weapons=frozenset({'shield'}) if shields else frozenset())
        profiles = (hero, enemy, replace(enemy, name='B', weapons=frozenset()))
        hero_policy = GroupPolicy('hero', weapon='hammer', offhand='blade', prefer_fast=True,
                                  split_targets=True, edge_mode='decline')
        enemy_policy = GroupPolicy('enemy', always_wait=True, edge_mode='decline', shield_react=shields)
        battle = GroupBattle(profiles, (hero_policy, enemy_policy, enemy_policy),
                             teams=('h', 'e', 'e'), initiative_roles=('player', 'npc', 'npc'),
                             initiative_tie_order=(0, 1, 2), seed=7, max_rounds=1, audit=True)
        # Hero initiative 20; both enemies 6. The strike then has forced faces.
        initiative = (6, 6, 6) + (1, 2, 1) * 2
        strikes = ((6, 6, 6) + (1, 2, 1) if shields else (1, 2, 1) * 2)
        battle.rng = FixedDice(initiative + strikes + (1, 2, 1) * 12)
        if fifo:
            with patch.object(GroupBattle, '_queue_reaction', Duel._queue_reaction):
                result = battle.run()
        else:
            result = battle.run()
        return result, profiles

    def test_fifo_reaction_regression_is_detected(self):
        result, profiles = self.forced_battle()
        self.assertEqual(audit_group_lifecycle(result.log, profiles), [])
        bad, profiles = self.forced_battle(fifo=True)
        self.assertTrue(any('reaction trigger processed in wrong order' in issue
                            for issue in audit_group_lifecycle(bad.log, profiles)))

    def test_shield_cannot_use_another_targets_failed_trigger(self):
        result, profiles = self.forced_battle(shields=True)
        self.assertEqual(audit_group_lifecycle(result.log, profiles), [])
        rows = deepcopy(list(result.log))
        miss = next(event for event in rows if event['type'] == 'group_hit_check' and not event['success'])
        for event in rows:
            if ((event['type'] == 'shield_activate' and event.get('cost') == 'reaction')
                    or (event['type'] == 'reaction_spent' and 'HR-04' in event['rules'])):
                event['trigger'] = miss['trigger']
        self.assertTrue(any('Shield reaction lacks a successful hit' in issue
                            for issue in audit_group_lifecycle(rows, profiles)))

    def test_hit_check_does_not_accept_boolean_as_zero_trouble(self):
        result, profiles = self.forced_battle()
        rows = deepcopy(list(result.log))
        hit = next(row for row in rows if row['type'] == 'group_hit_check' and row['troubles'] == 0)
        hit['troubles'] = False
        self.assertTrue(any('invalid group hit check field types' in issue
                            for issue in audit_group_lifecycle(rows, profiles)))

    def test_unconscious_living_turn_heals_but_dead_turn_does_not_resurrect(self):
        base = blacklight_profile()
        attacker = replace(base, name='Atacante', heroic=False)
        victim = replace(base, name='Vitima', max_health=8, heroic=False)
        ally = replace(base, name='Aliado', heroic=False)
        profiles = (attacker, victim, ally)
        attacker_policy = GroupPolicy('ataque', weapon='hammer', offhand='blade',
                                      prefer_fast=True, split_targets=True, edge_mode='decline')
        wait_policy = GroupPolicy('espera', always_wait=True, edge_mode='decline')
        for is_dead in (False, True):
            with self.subTest(dead=is_dead):
                battle = GroupBattle(profiles, (attacker_policy, wait_policy, wait_policy),
                                     teams=('e', 'h', 'h'), initiative_roles=('npc', 'player', 'npc'),
                                     initiative_tie_order=(0, 1, 2), seed=7, max_rounds=1, audit=True)
                first = (2, 1, 2) if is_dead else (6, 6, 6)
                battle.rng = FixedDice((6, 6, 6) + (5, 5, 5) + (3, 3, 3) + first + (6, 6, 6))
                battle.damage_rng = FixedDice(([1] if is_dead else [2]) * 80)
                result = battle.run()
                self.assertEqual(audit_group_lifecycle(result.log, profiles), [])
                skips = [event for event in result.log
                         if event['type'] == 'turn_skipped' and event['actor'] == 'Vitima']
                self.assertEqual(skips[0]['reason'], 'dead' if is_dead else 'unconscious')
                heals = [event for event in result.log if event['type'] == 'heal' and event['actor'] == 'Vitima']
                if is_dead:
                    self.assertEqual(heals, [])
                    self.assertLessEqual(result.final_health[1], -8)
                else:
                    # Sturdy 1: floor((8 - 1) / 2) * 2 + 3 = 9;
                    # Health 8 - 9 + Healing Factor 5 = 4.
                    self.assertEqual(result.final_health[1], 4)
                    self.assertEqual(heals[0]['effective'], 5)

    def test_stun_expires_at_scheduled_turn_of_unconscious_source(self):
        base = replace(blacklight_profile(), heroic=False)
        profiles = (replace(base, name='Fonte', max_health=12),
                    replace(base, name='Alvo', max_health=100),
                    replace(base, name='Atacante'), replace(base, name='Aliado'))
        policies = (GroupPolicy('fonte', weapon='hammer', edge_mode='decline'),
                    GroupPolicy('alvo', always_wait=True, edge_mode='decline'),
                    GroupPolicy('atacante', edge_mode='decline'),
                    GroupPolicy('aliado', always_wait=True, edge_mode='decline'))
        game = GroupBattle(profiles, policies, teams=('h', 'e', 'e', 'h'),
                           initiative_roles=('player', 'npc', 'npc', 'npc'),
                           initiative_tie_order=(0, 1, 2, 3), seed=7, max_rounds=2, audit=True)
        initiative = (6, 6, 6) + (2, 2, 2) + (5, 5, 5) + (4, 4, 4)
        game.rng = FixedDice(initiative + (2, 1, 2) + (6, 6, 6) * 2)
        game.damage_rng = FixedDice([2] * 100)
        result = game.run()
        self.assertEqual(audit_group_lifecycle(result.log, profiles), [])
        boundary = next(e for e in result.log if e['type'] == 'group_turn_boundary'
                        and e['actor'] == 'Fonte' and e['turn_count'] == 2)
        expiration = next(e for e in result.log if e['type'] == 'condition_instance_end'
                          and e['expires_on_actor'] == 'Fonte')
        skipped = next(e for e in result.log if e['type'] == 'turn_skipped'
                       and e['actor'] == 'Fonte')
        self.assertEqual(skipped['reason'], 'unconscious')
        self.assertLess(boundary['seq'], expiration['seq'])
        self.assertLess(expiration['seq'], skipped['seq'])
