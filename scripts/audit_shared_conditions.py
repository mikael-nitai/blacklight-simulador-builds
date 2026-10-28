"""Read-only audit of shared condition expiration across combat prototypes.

Run from the repository root with ``python -B -m scripts.audit_shared_conditions``.
Historical engine classes are loaded in isolated module namespaces from the
pre-migration commit; no files or result JSONs are written.
"""

from argparse import ArgumentParser
from dataclasses import asdict
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace

from blacklight.engine import Profile, blacklight_profile
from blacklight.policies import KITER, RulePolicy
from combatants.condition_bridge import (ConditionTiming, expire_at_turn_start,
                                         turn_start_plan)
from experimental.corridor import CorridorDuel
from experimental.focus_duel import FocusDuel, STRATEGIES
from experimental.group import GroupBattle
from experimental.group_policies import GroupPolicy, GROUP_ENEMY
from scripts.corridor_experiment import (POLICIES as CORRIDOR_POLICIES,
                                         gunners, seed_for as corridor_seed)
from scripts.focus_experiment import mentalist, seed_for as focus_seed
from scripts.group_experiment import (POLICIES as GROUP_POLICIES,
                                      scenarios as group_scenarios,
                                      seed_for as group_seed)
from scripts.verify_sources import verify_result
from .audit_manifest import audit_source_manifest, require_audit_sources_unchanged


ROOT = Path(__file__).resolve().parents[1]
BASE_REF = 'e84a7532a58f1dd2a0ba5792be6f5d1e064223a0'
DEMOS = {
    'group': 'group_pool_v2_demo_G2_shield_0.json',
    'focus': 'focus_pool_v2_demo_M4_F0_shield_0.json',
    'corridor': 'corridor_pool_v2_demo_L20_C2_fast_0.json',
}


def historical_class(relative: str, class_name: str):
    """Read one old source blob without replacing the imported live module."""
    result = subprocess.run(
        ['git', '--no-replace-objects', 'show', f'{BASE_REF}:{relative}'],
        cwd=ROOT, check=True, capture_output=True)
    name = 'experimental._audit_previous_' + Path(relative).stem
    module = ModuleType(name)
    module.__file__ = f'{BASE_REF}:{relative}'
    module.__package__ = 'experimental'
    sys.modules[name] = module
    exec(compile(result.stdout, module.__file__, 'exec'), module.__dict__)
    return getattr(module, class_name), sha256(result.stdout).hexdigest()


def normalized(result) -> dict:
    return json.loads(json.dumps(asdict(result)))


def profile(record: dict) -> Profile:
    fields = dict(record)
    for key in ('powers', 'traits', 'weapons'):
        fields[key] = frozenset(fields[key])
    return Profile(**fields)


def plan_oracle() -> int:
    """Compute due effects directly from the chosen roster and source clock."""
    checked = 0
    for size in (2, 3):
        choices = ((None, None),) + tuple(
            (source, deadline)
            for source in range(size) for deadline in (None, 1, 3))
        for actor in range(size):
            modes = ((True, tuple(range(size))),
                     (False, (1 - actor,))) if size == 2 else (
                         (False, tuple(range(size))),)
            for include_dodge, subjects in modes:
                for active_count, other_count, dodge_mask in product(
                        (1, 2, 3), (0, 2),
                        (0, 1 << actor, (1 << size) - 1)):
                    counts = tuple(active_count if i == actor else other_count
                                   for i in range(size))
                    for conditions in product(choices, repeat=size):
                        states = tuple(ConditionTiming(
                            bool(dodge_mask & (1 << i)), source, deadline)
                            for i, (source, deadline) in enumerate(conditions))
                        before = tuple((state.dodging, state.stunned_by,
                                        state.stun_deadline) for state in states)
                        plan = turn_start_plan(states, counts, actor,
                                               include_dodge=include_dodge,
                                               stun_subjects=subjects)
                        expired, remaining = [], []
                        if include_dodge and states[actor].dodging:
                            expired.append(('dodge', actor))
                        for subject in subjects:
                            state = states[subject]
                            if state.stunned_by is None:
                                continue
                            item = ('stunned', subject)
                            due = (state.stunned_by == actor and
                                   state.stun_deadline is not None and
                                   active_count >= state.stun_deadline)
                            (expired if due else remaining).append(item)
                        actual = (
                            [(item.kind, item.subject) for item in plan.expired],
                            [(item.kind, item.subject) for item in plan.remaining],
                        )
                        after = tuple((state.dodging, state.stunned_by,
                                       state.stun_deadline) for state in states)
                        if actual != (expired, remaining) or after != before:
                            raise AssertionError(('plan_oracle', size, actor,
                                                  counts, conditions, actual,
                                                  (expired, remaining)))
                        checked += 1
    return checked


def fake_fighters(states: tuple[ConditionTiming, ...]):
    return [SimpleNamespace(
        dodging=state.dodging,
        stunned_by=state.stunned_by,
        stun_expires_on_actor_turn=state.stun_deadline,
        profile=SimpleNamespace(name=f'F{i}'))
        for i, state in enumerate(states)]


def bridge_case(states: tuple[ConditionTiming, ...], counts: tuple[int, ...],
                actor: int, *, include_dodge: bool, subjects: tuple[int, ...],
                expected_events: list[tuple[str, str]],
                expected_flags: list[tuple[bool, int | None, int | None]]) -> None:
    fighters = fake_fighters(states)
    events = []
    def record(kind, rules, **data):
        events.append((kind, data['actor']))
    expire_at_turn_start(fighters, counts, actor, record,
                         include_dodge=include_dodge, stun_subjects=subjects)
    flags = [(f.dodging, f.stunned_by, f.stun_expires_on_actor_turn)
             for f in fighters]
    if events != expected_events or flags != expected_flags:
        raise AssertionError(('bridge_case', actor, events, expected_events,
                              flags, expected_flags))


def direct_bridge_oracles() -> int:
    """Check event order, multiple targets, autocast and ignored Dodge."""
    bridge_case(
        (ConditionTiming(True, 0, 1), ConditionTiming(False, 0, 1),
         ConditionTiming(False, 0, 1)), (1, 0, 0), 0,
        include_dodge=False, subjects=(0, 1, 2),
        expected_events=[('condition_end', 'F0'), ('condition_end', 'F1'),
                         ('condition_end', 'F2')],
        expected_flags=[(True, None, None), (False, None, None),
                        (False, None, None)])
    bridge_case(
        (ConditionTiming(True, 0, 1), ConditionTiming(False, 0, 1)),
        (1, 0), 0, include_dodge=True, subjects=(0, 1),
        expected_events=[('dodge_end', 'F0'), ('condition_end', 'F0'),
                         ('condition_end', 'F1')],
        expected_flags=[(False, None, None), (False, None, None)])
    bridge_case(
        (ConditionTiming(True, 0, 1), ConditionTiming(False, 0, 1)),
        (1, 0), 0, include_dodge=False, subjects=(1,),
        expected_events=[('condition_end', 'F1')],
        expected_flags=[(True, 0, 1), (False, None, None)])

    states = (ConditionTiming(False, 0, 1),)
    for broken in ('callback', 'name'):
        fighters = fake_fighters(states)
        if broken == 'name':
            fighters[0].profile.name = ''
        before = [(f.dodging, f.stunned_by, f.stun_expires_on_actor_turn)
                  for f in fighters]
        events = []
        record = None if broken == 'callback' else lambda *args, **kwargs: events.append(args)
        try:
            expire_at_turn_start(fighters, (1,), 0, record)
        except (TypeError, ValueError):
            pass
        else:
            raise AssertionError(('malformed_bridge_input_accepted', broken))
        after = [(f.dodging, f.stunned_by, f.stun_expires_on_actor_turn)
                 for f in fighters]
        if after != before or events:
            raise AssertionError(('partial_mutation_on_invalid_bridge', broken))
    return 5


def forced_turn_oracles(old_group=None, old_focus=None) -> int:
    """Exercise guards and self-stun through the actual turn entry points."""
    checks = 0

    def group_game(cls):
        game = cls(group_scenarios()[0][1], (GROUP_ENEMY,) * 3,
                   seed=1, audit=True)
        game.round = 1
        return game

    group_cases = (
        ('self_stun', 0, lambda game: (
            setattr(game.fighters[0], 'stunned_by', 0),
            setattr(game.fighters[0], 'stun_expires_on_actor_turn', 1)),
         ('condition_end', 'turn_start'), 1, None),
        ('bonus_self_stun', 0, lambda game: (
            setattr(game, 'round', 0),
            setattr(game, 'bonus_round', True),
            setattr(game.fighters[0], 'stunned_by', 0),
            setattr(game.fighters[0], 'stun_expires_on_actor_turn', 1)),
         ('condition_end', 'turn_start'), 1, None),
        ('two_targets', 0, lambda game: (
            setattr(game.fighters[1], 'stunned_by', 0),
            setattr(game.fighters[1], 'stun_expires_on_actor_turn', 1),
            setattr(game.fighters[2], 'stunned_by', 0),
            setattr(game.fighters[2], 'stun_expires_on_actor_turn', 1)),
         ('condition_end', 'condition_end', 'turn_start'), 1, None),
        ('unconscious_source', 0, lambda game: (
            setattr(game.fighters[0], 'health', 0),
            setattr(game.fighters[1], 'stunned_by', 0),
            setattr(game.fighters[1], 'stun_expires_on_actor_turn', 1)),
         (), 0, 0),
    )
    for label, actor, setup, prefix, expected_count, expected_stun in group_cases:
        games = ((group_game(old_group), group_game(GroupBattle))
                 if old_group is not None else (group_game(GroupBattle),))
        for game in games:
            setup(game)
            game._turn(actor)
            events = tuple(row['type'] for row in game.log)
            if events[:len(prefix)] != prefix or game.turn_counts[actor] != expected_count:
                raise AssertionError(('group_turn_oracle', label, events[:len(prefix)],
                                      game.turn_counts[actor]))
            if label in ('self_stun', 'bonus_self_stun') and game.fighters[0].stunned_by is not None:
                raise AssertionError('group self-stun did not expire')
            if label == 'bonus_self_stun' and not all(
                    row['round'] == 0 and row['bonus_round'] for row in game.log):
                raise AssertionError('group bonus round event metadata changed')
            if label == 'two_targets' and any(
                    game.fighters[i].stunned_by is not None for i in (1, 2)):
                raise AssertionError('group target stuns did not expire')
            if label == 'unconscious_source' and (
                    game.fighters[1].stunned_by != expected_stun or
                    game.active_actor is not None):
                raise AssertionError('unconscious group source advanced a clock')
        if (len(games) == 2 and
                ([vars(f) for f in games[0].fighters] !=
                 [vars(f) for f in games[1].fighters]
                 or games[0].log != games[1].log)):
            raise AssertionError(('group_forced_differential', label))
        checks += 1

    def focus_game(cls):
        game = cls(blacklight_profile(), mentalist(3), strategy='hammer',
                   shield_focus_reduction=0, seed=1, audit=True)
        game.round = 1
        return game

    focus_cases = (
        ('self_stun', 0, lambda game: (
            setattr(game.fighters[0], 'stunned_by', 0),
            setattr(game.fighters[0], 'stun_expires_on_actor_turn', 1)),
         ('turn_start', 'turn_skipped'), 1, 0),
        ('bonus_self_stun', 0, lambda game: (
            setattr(game, 'round', 0),
            setattr(game, 'bonus_round', True),
            setattr(game.fighters[0], 'stunned_by', 0),
            setattr(game.fighters[0], 'stun_expires_on_actor_turn', 1)),
         ('turn_start', 'turn_skipped'), 1, 0),
        ('other_target', 0, lambda game: (
            setattr(game.fighters[1], 'stunned_by', 0),
            setattr(game.fighters[1], 'stun_expires_on_actor_turn', 1)),
         ('condition_end', 'turn_start'), 1, None),
        ('shattered_source', 1, lambda game: (
            setattr(game.fighters[1], 'focus', -game.fighters[1].profile.max_focus),
            setattr(game.fighters[0], 'stunned_by', 1),
            setattr(game.fighters[0], 'stun_expires_on_actor_turn', 1)),
         (), 0, 1),
    )
    for label, actor, setup, prefix, expected_count, expected_stun in focus_cases:
        games = ((focus_game(old_focus), focus_game(FocusDuel))
                 if old_focus is not None else (focus_game(FocusDuel),))
        for game in games:
            setup(game)
            game._turn(actor)
            events = tuple(row['type'] for row in game.log)
            if events[:len(prefix)] != prefix or game.turn_counts[actor] != expected_count:
                raise AssertionError(('focus_turn_oracle', label, events[:len(prefix)],
                                      game.turn_counts[actor]))
            subject = 1 if label == 'other_target' else 0
            if game.fighters[subject].stunned_by != expected_stun:
                raise AssertionError(('focus_stun_scope', label,
                                      game.fighters[subject].stunned_by))
            if label == 'bonus_self_stun' and not all(
                    row['round'] == 0 and row['bonus_round'] for row in game.log):
                raise AssertionError('focus bonus round event metadata changed')
        if (len(games) == 2 and
                ([vars(f) for f in games[0].fighters] !=
                 [vars(f) for f in games[1].fighters]
                 or games[0].log != games[1].log)):
            raise AssertionError(('focus_forced_differential', label))
        checks += 1
    return checks


def historical_differential(old_group, old_focus, old_corridor) -> dict[str, int]:
    """Compare 300 fights with both engines using today's shared helpers.

    Historical classes isolate the condition-call migration, not old damage
    arithmetic: dice, Fighter, damage pools and policies are current imports.
    """
    counts = {'group': 0, 'focus': 0, 'corridor': 0}
    for scenario_id, profiles in group_scenarios():
        for policy in GROUP_POLICIES:
            for index in range(10):
                seed = group_seed('dev', scenario_id, policy.name, index)
                args = (profiles, (policy, GROUP_ENEMY, GROUP_ENEMY))
                old = old_group(*args, seed=seed, audit=True).run()
                new = GroupBattle(*args, seed=seed, audit=True).run()
                if normalized(old) != normalized(new):
                    raise AssertionError(('group_differential', scenario_id,
                                          policy.name, index))
                counts['group'] += 1
    for rank in (3, 4):
        profiles = (blacklight_profile(), mentalist(rank))
        for reduction in (0, 2):
            variant = f'F{reduction}'
            for strategy in STRATEGIES:
                for index in range(10):
                    seed = focus_seed('dev', f'M{rank}', variant, strategy, index)
                    kwargs = dict(strategy=strategy,
                                  shield_focus_reduction=reduction,
                                  seed=seed, audit=True)
                    old = old_focus(*profiles, **kwargs).run()
                    new = FocusDuel(*profiles, **kwargs).run()
                    if normalized(old) != normalized(new):
                        raise AssertionError(('focus_differential', rank,
                                              reduction, strategy, index))
                    counts['focus'] += 1
    for length in (12, 20):
        for opponent_id, opponent in gunners():
            profiles = (blacklight_profile(), opponent)
            for policy in CORRIDOR_POLICIES:
                for index in range(10):
                    seed = corridor_seed('dev', length, opponent_id,
                                         policy.name, index)
                    kwargs = dict(seed=seed, length=length,
                                  initial_positions=(0, 8), audit=True)
                    old_game = old_corridor(profiles, (policy, KITER), **kwargs)
                    new_game = CorridorDuel(profiles, (policy, KITER), **kwargs)
                    old = normalized(old_game.run())
                    new = normalized(new_game.run())
                    geometry = ('positions', 'wall_reached', 'contact_occurred')
                    if (old != new or
                            any(getattr(old_game, name) != getattr(new_game, name)
                                for name in geometry)):
                        raise AssertionError(('corridor_differential', length,
                                              opponent_id, policy.name, index))
                    counts['corridor'] += 1
    return counts


def frozen_demo_replays(old_group, old_focus, old_corridor) -> dict[str, str]:
    """Rebuild each saved full trace and compare all extra corridor geometry."""
    hashes = {}
    for kind, name in DEMOS.items():
        path = ROOT / 'results' / name
        mode, issues = verify_result(path, root=ROOT)
        if issues or not mode.startswith(('snapshot:', 'live+snapshot:')):
            raise AssertionError(('unverified_frozen_demo', name, mode, issues))
        saved = json.loads(path.read_text(encoding='utf-8'))
        profiles = tuple(profile(row) for row in saved['profiles'])
        if kind == 'group':
            policies = tuple(GroupPolicy(**row) for row in saved['policies'])
            constructors = (old_group, GroupBattle)
            games = (ctor(profiles, policies, seed=saved['seed'], audit=True)
                     for ctor in constructors)
        elif kind == 'focus':
            reduction = 0 if saved['variant'] == 'F0' else 2
            constructors = (old_focus, FocusDuel)
            games = (ctor(*profiles, strategy=saved['strategy'],
                          shield_focus_reduction=reduction,
                          seed=saved['seed'], audit=True)
                     for ctor in constructors)
        else:
            policies = tuple(RulePolicy(**row) for row in saved['policies'])
            constructors = (old_corridor, CorridorDuel)
            games = (ctor(profiles, policies, seed=saved['seed'],
                          length=saved['length'],
                          initial_positions=tuple(saved['initial_positions']),
                          audit=True) for ctor in constructors)
        for game in games:
            if normalized(game.run()) != saved['result']:
                raise AssertionError(('frozen_demo_result', name,
                                      type(game).__name__))
            if kind == 'corridor':
                if (game.positions != saved['final_positions']
                        or game.wall_reached != saved['wall_reached']
                        or game.contact_occurred != saved['contact_occurred']):
                    raise AssertionError(('frozen_demo_geometry', name,
                                          type(game).__name__))
        hashes[name] = sha256(path.read_bytes()).hexdigest()
    return hashes


def main() -> None:
    sources = audit_source_manifest()
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--timing-only', action='store_true',
                        help='Run current timing oracles without historical fight/replay comparisons')
    args = parser.parse_args()
    if args.timing_only:
        old_group = old_focus = old_corridor = None
        baseline_hashes = {}
    else:
        old_group, group_hash = historical_class('experimental/group.py', 'GroupBattle')
        old_focus, focus_hash = historical_class('experimental/focus_duel.py', 'FocusDuel')
        old_corridor, corridor_hash = historical_class('experimental/corridor.py',
                                                      'CorridorDuel')
        baseline_hashes = {
            'experimental/group.py': group_hash,
            'experimental/focus_duel.py': focus_hash,
            'experimental/corridor.py': corridor_hash,
        }
    plan_cases = plan_oracle()
    direct_cases = direct_bridge_oracles()
    forced_cases = forced_turn_oracles(old_group, old_focus)
    differential = (None if args.timing_only else
                    historical_differential(old_group, old_focus, old_corridor))
    demos = ({} if args.timing_only else
             frozen_demo_replays(old_group, old_focus, old_corridor))
    require_audit_sources_unchanged(sources)
    print(json.dumps({
        'status': 'pass',
        'mode': 'timing-only' if args.timing_only else 'full-pre-fast-comparison',
        'direct_plan_cases': plan_cases,
        'direct_bridge_cases': direct_cases,
        'forced_turn_cases': forced_cases,
        'historical_differential_fights': differential,
        'frozen_full_trace_demos': len(demos),
        'frozen_demo_sha256': demos,
        'baseline_commit': BASE_REF,
        'baseline_source_sha256': baseline_hashes,
        'source_sha256': sources,
        'snapshot_index_sha256': sha256(
            (ROOT / 'results' / 'source_snapshots.json').read_bytes()).hexdigest(),
        'coverage_limits': [
            'Only start-turn Dodge and Stunned are bridged.',
            'Group and Focus intentionally ignore Dodge; Focus examines only the other subject.',
            'Round boundaries are not wired to these duel loops.',
            'Historical engine classes share current dice, Fighter, damage-pool and policy helpers; the differential isolates timing, not historical damage arithmetic.',
            'Frozen demo replay equality may change after an approved damage-rule revision and must not be attributed to timing alone.',
            'Three frozen demos and 300 sampled fights do not recompute historical summary tables.',
        ],
    }, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
