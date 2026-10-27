"""Read-only, independent timing audit for the first modular lifecycle bridge.

Run from the repository root with ``python -B -m scripts.audit_modular_lifecycle``.
The bridge currently projects only Dodge and Stunned at turn start. Round
boundaries and effect instances are tested as pure timing primitives; they are
not claimed to be connected to Duel's event loop.
"""

from dataclasses import asdict, replace
from hashlib import sha256
from itertools import product
import json
from pathlib import Path

from blacklight.engine import Duel, Profile
from blacklight.policies import ATTACK, RulePolicy
from combatants.duel_adapter import compile_duel
from combatants.lifecycle import Boundary, TimePoint, TimedEffect, expiration_plan
from combatants.modular_duel import ModularDuel
from combatants.sheets import parse_sheet
from scripts.verify_sources import verify_result


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    'blacklight/dice.py',
    'blacklight/engine.py',
    'blacklight/policies.py',
    'blacklight/pool_damage.py',
    'combatants/actions.py',
    'combatants/duel_adapter.py',
    'combatants/lifecycle.py',
    'combatants/modular_duel.py',
    'combatants/sheets.py',
    'scripts/audit_modular_lifecycle.py',
    'scripts/verify_sources.py',
)


def timing_oracle() -> dict[str, int]:
    """Compare every small clock pair with a direct boundary/actor/count oracle."""
    points = tuple(
        TimePoint(boundary, occurrence, actor)
        for boundary in Boundary
        for occurrence in ((0, 1, 2, 3) if boundary in
                           (Boundary.ROUND_START, Boundary.ROUND_END) else (1, 2, 3))
        for actor in ((0, 1, 7) if boundary in
                      (Boundary.TURN_START, Boundary.TURN_END) else (None,))
    )
    comparisons = 0
    for now, deadline in product(points, repeat=2):
        pending = TimedEffect('one', 'stunned', 0, 1, (deadline,), ('AUDIT',))
        plan = expiration_plan((pending,), now)
        due = (now.boundary is deadline.boundary and now.actor == deadline.actor
               and now.occurrence >= deadline.occurrence)
        expected = ((pending,), ()) if due else ((), (pending,))
        if (plan.expired, plan.remaining) != expected:
            raise AssertionError(('clock_mismatch', now, deadline))
        comparisons += 1

    for boundary in (Boundary.TURN_START, Boundary.TURN_END):
        try:
            TimePoint(boundary, 0, 0)
        except ValueError:
            pass
        else:
            raise AssertionError(('turn_zero_was_accepted', boundary))
    for boundary in (Boundary.ROUND_START, Boundary.ROUND_END):
        if TimePoint(boundary, 0).occurrence != 0:
            raise AssertionError(('round_zero_was_rejected', boundary))

    source_deadline = TimePoint(Boundary.TURN_START, 2, 1)
    round_fallback = TimePoint(Boundary.ROUND_END, 0)
    fallback = TimedEffect('fallback', 'stunned', 0, 1,
                           (source_deadline, round_fallback), ('AUDIT',))
    for now, due in (
        (TimePoint(Boundary.TURN_START, 2, 0), False),
        (source_deadline, True),
        (round_fallback, True),
    ):
        plan = expiration_plan((fallback,), now)
        if bool(plan.expired) != due:
            raise AssertionError(('source_or_round_fallback', now))

    first = TimedEffect('first', 'stunned', 0, 1,
                        (TimePoint(Boundary.TURN_START, 1, 1),), ('AUDIT',))
    second = TimedEffect('second', 'stunned', 0, 1,
                         (TimePoint(Boundary.TURN_START, 2, 1),), ('AUDIT',))
    indefinite = TimedEffect('indefinite', 'stunned', 0, None, (), ('AUDIT',))
    instances = (first, second, indefinite)
    plan = expiration_plan(instances, TimePoint(Boundary.TURN_START, 1, 1))
    if (plan.expired, plan.remaining) != ((first,), (second, indefinite)):
        raise AssertionError('parallel effects lost identity or order')
    if instances != (first, second, indefinite):
        raise AssertionError('expiration planning mutated its input')
    try:
        expiration_plan((first, first), TimePoint(Boundary.TURN_START, 1, 1))
    except ValueError:
        pass
    else:
        raise AssertionError('duplicate effect token was accepted')
    return {'clock_pairs': comparisons, 'round_zero_cases': 2,
            'turn_zero_rejections': 2, 'alternative_deadline_cases': 3,
            'parallel_instance_cases': 1}


def battle(cls: type[Duel]) -> Duel:
    profiles = tuple(Profile(name, 3, 90, 60, 4, 2, 3, 2, 14, 12, 5)
                     for name in ('A', 'B'))
    wait = replace(ATTACK, always_wait=True)
    game = cls(profiles, (wait, wait), seed=8, audit=True)
    game.round = 1
    return game


def bridge_oracle() -> int:
    """Check expected flags and log order, then compare complete reference state."""
    stun_states = ((None, None), (0, None), (0, 1), (0, 3),
                   (1, None), (1, 1), (1, 3))
    checked = 0
    for actor, active_count, other_count, dodge0, dodge1, stun0, stun1 in product(
            (0, 1), (1, 2, 3), (1, 2), (False, True), (False, True),
            stun_states, stun_states):
        counts = [other_count, other_count]
        counts[actor] = active_count
        reference, modular = battle(Duel), battle(ModularDuel)
        expected_events = []
        for game in (reference, modular):
            game.turn_counts[:] = counts
            game.fighters[0].dodging = dodge0
            game.fighters[1].dodging = dodge1
            for fighter, (source, deadline) in zip(game.fighters, (stun0, stun1)):
                fighter.stunned_by = source
                fighter.stun_expires_on_actor_turn = deadline
        expected_fighters = [vars(fighter).copy() for fighter in reference.fighters]
        if (dodge0, dodge1)[actor]:
            expected_events.append(('dodge_end', ('A', 'B')[actor], None))
        expected_fighters[actor]['dodging'] = False
        for subject, (source, deadline) in enumerate((stun0, stun1)):
            if source == actor and deadline is not None and active_count >= deadline:
                expected_fighters[subject]['stunned_by'] = None
                expected_fighters[subject]['stun_expires_on_actor_turn'] = None
                expected_events.append(('condition_end', ('A', 'B')[subject],
                                        'stunned'))
        for game in (reference, modular):
            game._start_turn_effects(actor)
            actual_events = [(row['type'], row.get('actor'), row.get('condition'))
                             for row in game.log]
            if actual_events != expected_events:
                raise AssertionError(('event_oracle', actor, counts, stun0, stun1,
                                      actual_events, expected_events))
            if [vars(fighter) for fighter in game.fighters] != expected_fighters:
                raise AssertionError(('state_oracle', actor, counts, stun0, stun1))
            if game.turn_counts != counts:
                raise AssertionError(('turn_counter_mutated', actor, counts))
        if (reference.log != modular.log or
                [vars(fighter) for fighter in reference.fighters] !=
                [vars(fighter) for fighter in modular.fighters]):
            raise AssertionError(('reference_mismatch', actor, counts, stun0, stun1))
        checked += 1
    return checked


def frozen_replay_oracle() -> tuple[int, dict[str, str]]:
    paths = [ROOT / 'results' / name for name in (
        'generic_sheet_dodge_demo.json', 'generic_sheet_modular_heal_demo.json',
        'generic_sheet_rank4_demo.json', 'generic_sheet_stance_demo.json',
        'generic_sheet_standard_shield_demo.json')]
    digests = {}
    for path in paths:
        mode, issues = verify_result(path, root=ROOT)
        if issues or not mode.startswith(('snapshot:', 'live+snapshot:')):
            raise AssertionError(('unverified_frozen_replay', path.name, mode, issues))
        stored = json.loads(path.read_text(encoding='utf-8'))
        profiles = tuple(compile_duel(parse_sheet(data)) for data in stored['sheets'])
        policies = tuple(RulePolicy(**data) for data in stored['policies'])
        for cls in (Duel, ModularDuel):
            game = cls(profiles, policies, seed=stored['seed'],
                       initial_distance=stored['initial_distance'],
                       max_rounds=stored['max_rounds'], audit=True)
            replay = json.loads(json.dumps(asdict(game.run())))
            if replay != stored['result']:
                raise AssertionError(('frozen_replay_mismatch', path.name, cls.__name__))
        digests[path.name] = sha256(path.read_bytes()).hexdigest()
    return len(paths), digests


def main() -> None:
    timing = timing_oracle()
    bridge_states = bridge_oracle()
    frozen_replays, result_hashes = frozen_replay_oracle()
    source_hashes = {name: sha256((ROOT / name).read_bytes()).hexdigest()
                     for name in SOURCES}
    print(json.dumps({
        'status': 'pass',
        'timing_oracle': timing,
        'bridge_states': bridge_states,
        'frozen_generic_replays': frozen_replays,
        'frozen_result_sha256': result_hashes,
        'snapshot_index_sha256': sha256(
            (ROOT / 'results' / 'source_snapshots.json').read_bytes()).hexdigest(),
        'source_sha256': source_hashes,
        'coverage_limits': [
            'Round start and round end are pure clocks, not wired into Duel.',
            'The bridge projects Dodge and Stunned only at turn start.',
            'Legacy fighter flags remain the authoritative mutable state.',
            'This audit does not establish a complete effect catalogue.',
        ],
    }, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
