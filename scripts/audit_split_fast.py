"""Read-only independent audit of the table's two-check Fast Strikes contract.

Run with ``python -B -m scripts.audit_split_fast`` from the repository root.
The explicit outcome table below is calculated without production damage
helpers. Tagged RNG, policy decisions and events check the execution order.
"""

from copy import deepcopy
from dataclasses import replace
from itertools import product
import json

from blacklight.audit import audit_log
from blacklight.engine import Action, IllegalAction, Profile, blacklight_profile
from blacklight.policies import RulePolicy
from combatants.split_fast import FastAction, SplitFastDuel, SplitFastPolicy
from .audit_manifest import audit_source_manifest, require_audit_sources_unchanged


ROLLS = {'common': (6, 6, 6), 'fantastic': (2, 1, 2), 'miss': (2, 2, 2)}
ONE_FACES = {
    'hammer': {'common': 27, 'fantastic': 54, 'miss': 0},
    'blade': {'common': 21, 'fantastic': 48, 'miss': 0},
    'claw': {'common': 21, 'fantastic': 48, 'miss': 0},
    'bare': {'common': 21, 'fantastic': 42, 'miss': 0},
}
class TaggedDice:
    def __init__(self, values, timeline, label):
        self.values = iter(values)
        self.timeline = timeline
        self.label = label

    def randint(self, low, high):
        value = next(self.values)
        if not low <= value <= high:
            raise AssertionError(('invalid_forced_die', self.label, value))
        self.timeline.append(('rng', self.label, value))
        return value


class SpyPolicy:
    def __init__(self, delegate, timeline, label):
        self.delegate = delegate
        self.timeline = timeline
        self.label = label

    def __getattr__(self, name):
        return getattr(self.delegate, name)

    def use_shield_reaction(self, observation, incoming_kind):
        self.timeline.append(('decision', self.label, 'shield'))
        return self.delegate.use_shield_reaction(observation, incoming_kind)

    def use_riposte(self, observation):
        self.timeline.append(('decision', self.label, 'riposte'))
        return self.delegate.use_riposte(observation)


def make_game(rolls, *, hero=None, foe=None, policy=None, foe_policy=None,
              stack_stunned=False):
    hero = hero or replace(blacklight_profile(), heroic=False)
    foe = foe or Profile('Target', 3, 1000, 90, 4, 2, 3, 2, 14, 12, 5)
    policy = policy or SplitFastPolicy(
        'control', weapon='hammer', offhand='blade', prefer_fast=True,
        effect_limb=0, edge_mode='decline', riposte=False)
    foe_policy = foe_policy or RulePolicy('target', edge_mode='decline', riposte=False)
    game = SplitFastDuel((hero, foe), (policy, foe_policy), seed=1, audit=True,
                         stack_stunned_edge=stack_stunned)
    game.round = 1
    game._reset_reactions_for_round()
    game.active_actor = 0
    game.fighters[0].standard_available = True
    timeline = []
    game.rng = TaggedDice(rolls, timeline, 'hit')
    game.damage_rng = TaggedDice([1] * 200, timeline, 'damage')
    game.policies = (SpyPolicy(policy, timeline, 'attacker'),
                     SpyPolicy(foe_policy, timeline, 'defender'))
    original_record = game._record

    def record(kind, rules, **data):
        timeline.append(('event', kind, data.get('limb')))
        original_record(kind, rules, **data)

    game._record = record
    return game, timeline


def audit(game, log=None):
    trace = game.log if log is None else log
    return audit_log(trace,
                     {fighter.profile.name: fighter.profile.max_health
                      for fighter in game.fighters},
                     {fighter.profile.name: fighter.profile.max_focus
                      for fighter in game.fighters})


def events(game, kind):
    return [row for row in game.log if row['type'] == kind]


def assert_clean(game, label):
    issues = audit(game)
    if issues:
        raise AssertionError((label, 'valid_log_rejected', issues))


def chronology_oracles() -> int:
    game, timeline = make_game(ROLLS['fantastic'] + ROLLS['miss'],
                               stack_stunned=True)
    game._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=0))
    hit_positions = [i for i, item in enumerate(timeline)
                     if item[:2] == ('rng', 'hit')]
    damage_positions = [i for i, item in enumerate(timeline)
                        if item[:2] == ('rng', 'damage')]
    attacks = events(game, 'attack')
    if (len(hit_positions) != 6 or not damage_positions
            or max(hit_positions) >= min(damage_positions)
            or [row['edges'] for row in attacks] != [2, 2]
            or [row['success'] for row in attacks] != [True, False]
            or game.fighters[1].stunned_by != 0):
        raise AssertionError(('two_prepared_checks_or_stun_edge', timeline[:15]))
    check_seq = [row['seq'] for row in events(game, 'fast_limb_check')]
    first_resolution = min(row['seq'] for row in events(game, 'fast_limb_start'))
    if len(check_seq) != 2 or max(check_seq) >= first_resolution:
        raise AssertionError('both check events must precede either limb')
    assert_clean(game, 'chronology')

    shielded = Profile('Target', 3, 1000, 90, 4, 2, 3, 2, 14, 12, 5,
                       health_dr=1, weapons=frozenset({'shield'}))
    defender_policy = RulePolicy('shield', shield_react=True,
                                 edge_mode='decline', riposte=False)
    game, timeline = make_game(ROLLS['common'] * 2, foe=shielded,
                               foe_policy=defender_policy)
    game._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=0))
    last_check = max(i for i, item in enumerate(timeline)
                     if item[:2] == ('event', 'fast_limb_check'))
    shield_decision = next(i for i, item in enumerate(timeline)
                           if item == ('decision', 'defender', 'shield'))
    shield_event = next(i for i, item in enumerate(timeline)
                        if item[:2] == ('event', 'shield_activate'))
    first_damage = next(i for i, item in enumerate(timeline)
                        if item[:2] == ('rng', 'damage'))
    if (not last_check < shield_decision < shield_event < first_damage
            or 1000 - game.fighters[1].health != 30
            or [row['reduction'] for row in events(game, 'attack')] != [3, 3]):
        raise AssertionError(('shield_timing_or_reduction', timeline[:20]))
    assert_clean(game, 'shield')

    riposter = Profile('Target', 3, 1000, 90, 4, 2, 3, 2, 14, 12, 5,
                       powers=frozenset({'riposte'}))
    game, timeline = make_game(ROLLS['miss'] + ROLLS['fantastic'], foe=riposter,
                               foe_policy=RulePolicy('riposte', riposte=True,
                                                     edge_mode='decline'))
    game._act(0, FastAction('blade_fast', offhand='hammer', effect_limb=1))
    log = game.log
    attack_seq = [row['seq'] for row in events(game, 'attack')]
    stun_seq = [row['seq'] for row in events(game, 'condition_start')
                if row['condition'] == 'stunned']
    end_seq = events(game, 'fast_use_end')[0]['seq']
    if (len(attack_seq) != 2 or len(stun_seq) != 1
            or not max(attack_seq) < end_seq
            or not stun_seq[0] < end_seq
            or game.fighters[1].ripostes != 0
            or any('POW-06' in row.get('rules', ())
                   for row in events(game, 'reaction_spent'))):
        raise AssertionError(('stun_before_riposte', [row['type'] for row in log]))
    assert_clean(game, 'stun_before_riposte')

    reroll_policy = SplitFastPolicy(
        'reroll', weapon='hammer', offhand='blade', prefer_fast=True,
        effect_limb=0, edge_mode='marvel', riposte=False)
    game, timeline = make_game((2, 2, 2, 6, 6) * 2, policy=reroll_policy)
    game._fast_use(0, FastAction('hammer_fast', offhand='blade', effect_limb=0),
                   bonus_action=False)
    hits = [i for i, item in enumerate(timeline) if item[:2] == ('rng', 'hit')]
    damage = [i for i, item in enumerate(timeline) if item[:2] == ('rng', 'damage')]
    checks = events(game, 'fast_limb_check')
    if (len(hits) != 10 or not damage or max(hits) >= min(damage)
            or [row['edges'] for row in checks] != [2, 2]
            or [len(row['rerolls']) for row in checks] != [2, 2]):
        raise AssertionError(('two_edges_really_rerolled_per_limb', timeline[:20]))
    assert_clean(game, 'two_rerolls_per_limb')
    return 4


def outcome_grid() -> int:
    """Independent result/effect combinations with fixed damage faces."""
    checked = 0
    weapon_pairs = (('hammer', 'blade', 'hammer_fast', 'blade'),
                    ('blade', 'hammer', 'blade_fast', 'hammer'),
                    ('blade', 'blade', 'blade_fast', None),
                    ('claw', 'hammer', 'claw_fast', 'hammer'),
                    ('hammer', 'hammer', 'hammer_fast', None),
                    ('bare', 'bare', 'fast_strikes', None))
    for first_weapon, second_weapon, kind, offhand in weapon_pairs:
        for selected, first_outcome, second_outcome in product(
                (0, 1), ROLLS, ROLLS):
            game, _ = make_game(ROLLS[first_outcome] + ROLLS[second_outcome])
            eligible, _ = game._fast_use(
                0, FastAction(kind, offhand=offhand, effect_limb=selected),
                bonus_action=False)
            outcomes = (first_outcome, second_outcome)
            weapons = (first_weapon, second_weapon)
            expected_components = [ONE_FACES[weapon][outcome]
                                   for weapon, outcome in zip(weapons, outcomes)]
            attacks = events(game, 'attack')
            selected_weapon, selected_outcome = weapons[selected], outcomes[selected]
            bleed = 5 if ((selected_weapon == 'blade' and selected_outcome != 'miss')
                          or (selected_weapon == 'claw' and
                              selected_outcome == 'fantastic')) else 0
            limb_stage = int(selected_weapon == 'blade' and
                             selected_outcome == 'fantastic')
            stun = (0 if selected_weapon == 'hammer' and
                    selected_outcome == 'fantastic' else None)
            bonus = bool(limb_stage)
            if (1000 - game.fighters[1].health != sum(expected_components)
                    or [row['calculated_damage'] for row in attacks] != expected_components
                    or [row['effects_enabled'] for row in attacks] !=
                    [limb == selected for limb in (0, 1)]
                    or game.fighters[1].bleeding != bleed
                    or game.fighters[1].limb_stage != limb_stage
                    or game.fighters[1].stunned_by != stun
                    or game.fighters[0].stuns_applied != int(stun is not None)
                    or eligible != bonus
                    or game.fighters[0].attacks != 2
                    or game.fighters[0].hits != sum(outcome != 'miss' for outcome in outcomes)
                    or game.fighters[0].fantastic_hits !=
                    sum(outcome == 'fantastic' for outcome in outcomes)):
                raise AssertionError(('outcome_grid', weapons, selected, outcomes,
                                      expected_components))
            assert_clean(game, ('outcome_grid', weapons, selected, outcomes))
            checked += 1
    return checked


def boundary_and_bonus_oracles() -> int:
    # Rank 1, bare Fast: N=1 before DR, even ability bonus +6.
    hero = replace(blacklight_profile(), rank=1, melee_bonus=0,
                   weapons=frozenset(), heroic=False)
    for dr, expected in ((0, 3), (1, 0)):
        foe = Profile('Target', 3, 1000, 90, 4, 2, 3, 2, 14, 12, 5,
                      health_dr=dr)
        game, timeline = make_game(ROLLS['common'] + ROLLS['miss'],
                                   hero=hero, foe=foe)
        game._fast_use(0, FastAction('fast_strikes', effect_limb=0),
                       bonus_action=False)
        if (1000 - game.fighters[1].health != expected
                or any(item[:2] == ('rng', 'damage') for item in timeline)):
            raise AssertionError(('zero_dice_bonus', dr, expected))
        assert_clean(game, ('zero_dice_bonus', dr))

    policy = SplitFastPolicy('blade', weapon='blade', offhand='hammer',
                             prefer_fast=True, effect_limb=0,
                             edge_mode='decline', riposte=False)
    game, timeline = make_game(ROLLS['fantastic'] * 4, policy=policy)
    game._act(0, FastAction('blade_fast', offhand='hammer', effect_limb=0))
    if (len(events(game, 'fast_limb_check')) != 4
            or len(events(game, 'fast_use_start')) != 2
            or len(events(game, 'blade_bonus')) != 1
            or game.fighters[0].attacks != 4
            or game.fighters[0].blade_bonus_actions != 1
            or 1000 - game.fighters[1].health != 204
            or sum(item[:2] == ('rng', 'hit') for item in timeline) != 12):
        raise AssertionError('Blade Fantastic did not grant exactly one new use')
    assert_clean(game, 'blade_bonus')

    game, timeline = make_game(ROLLS['common'] * 2)
    before = (game.fighters[0].standard_available, len(game.log))
    try:
        game._act(0, Action('hammer_fast', offhand='blade'))
    except IllegalAction:
        pass
    else:
        raise AssertionError('Fast action without selected limb was accepted')
    if ((game.fighters[0].standard_available, len(game.log)) != before or timeline):
        raise AssertionError('Invalid Fast action consumed resources or RNG')
    for invalid in (None, False, 0.0, -1, 2):
        try:
            FastAction('blade_fast', effect_limb=invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(('invalid_effect_limb', invalid))
    return 4


def resequence(log):
    for seq, row in enumerate(log, 1):
        row['seq'] = seq
    return log


def falsification_oracles() -> int:
    checked = 0
    game, _ = make_game(ROLLS['miss'] + ROLLS['common'])
    game._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=0))
    assert_clean(game, 'queue_control')
    for target in ('before_first_check', 'between_checks', 'after_use_end'):
        altered = deepcopy(game.log)
        queue = next(row for row in altered if row['type'] == 'reaction_queued')
        altered.remove(queue)
        if target == 'after_use_end':
            position = next(i for i, row in enumerate(altered)
                            if row['type'] == 'fast_use_end') + 1
        else:
            checks = [i for i, row in enumerate(altered)
                      if row['type'] == 'fast_limb_check']
            position = checks[0 if target == 'before_first_check' else 1]
        altered.insert(position, queue)
        if not audit(game, resequence(altered)):
            raise AssertionError(('forged_queue_timing_accepted', target))
        checked += 1

    shielded = Profile('Target', 3, 1000, 90, 4, 2, 3, 2, 14, 12, 5,
                       health_dr=1, weapons=frozenset({'shield'}))
    defender_policy = RulePolicy('shield', shield_react=True,
                                 edge_mode='decline', riposte=False)
    game, _ = make_game(ROLLS['common'] * 2, foe=shielded,
                        foe_policy=defender_policy)
    game._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=0))
    assert_clean(game, 'shield_control')
    altered = deepcopy(game.log)
    shield_events = [row for row in altered
                     if row['type'] in ('reaction_spent', 'shield_activate')]
    for row in shield_events:
        altered.remove(row)
    position = next(i for i, row in enumerate(altered)
                    if row['type'] == 'attack') + 1
    altered[position:position] = shield_events
    if not audit(game, resequence(altered)):
        raise AssertionError('forged_shield_after_first_damage_accepted')
    checked += 1

    game, _ = make_game(ROLLS['common'] + ROLLS['fantastic'])
    game._act(0, FastAction('hammer_fast', offhand='blade', effect_limb=0))
    altered = deepcopy(game.log)
    unchosen = next(row for row in altered
                    if row['type'] == 'attack' and row['limb'] == 1)
    unchosen['effect_limb'], unchosen['effects_enabled'] = 1, True
    if not audit(game, altered):
        raise AssertionError('forged_unselected_effect_accepted')
    checked += 1
    return checked


def main() -> None:
    hashes = audit_source_manifest()
    chronology = chronology_oracles()
    grid = outcome_grid()
    boundaries = boundary_and_bonus_oracles()
    falsifications = falsification_oracles()
    require_audit_sources_unchanged(hashes)
    print(json.dumps({
        'status': 'pass',
        'chronology_cases': chronology,
        'outcome_grid_cases': grid,
        'boundary_bonus_validation_cases': boundaries,
        'forged_logs_rejected': falsifications,
        'source_sha256': hashes,
        'scope': 'SplitFastDuel two-actor version; historical Duel and group results are separate',
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
