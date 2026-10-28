"""Independent audit of experimental group timing, conditions and interrupts.

The log is checked against the declared experimental contract, including the
provisional parallel-source Stunned and FIFO initial limb ordering. This is not
an oracle for unimplemented game rules or arbitrary coordinated falsification.
"""

from collections import deque


def audit_group_lifecycle(log, profiles):
    names = tuple(profile.name for profile in profiles)
    if len(names) < 2 or len(set(names)) != len(names):
        raise ValueError('Distinct named group participants are required')
    health = {p.name: p.max_health for p in profiles}
    maximum = {p.name: p.max_health for p in profiles}
    counts = dict.fromkeys(names, 0)
    stunned = {}  # token -> (target, source, deadline)
    dodging = set()
    pending = deque()
    checks, attacks = {}, {}
    issues = []
    active = phase = boundary = None
    due, condition_ends, dodge_due = set(), set(), False
    skip_reason = None
    skip_seen = False
    last_dequeued = None
    expected_queue = None
    action_events = {'movement', 'group_grid_move', 'fast_use_start', 'fast_limb_check',
                     'fast_limb_start', 'fast_use_end', 'stance', 'dodge',
                     'focus_spent', 'wait', 'condition_treatment', 'blade_bonus'}
    boundary_events = {'condition_instance_end', 'condition_end', 'dodge_end', 'turn_start'}
    for event in log:
        kind, actor, seq = event.get('type'), event.get('actor'), event.get('seq')
        event_phase = (event.get('round'), event.get('bonus_round'))
        if expected_queue is not None and kind != 'reaction_queued':
            issues.append(f'event {seq}: missing reaction queue after a failed close attack')
            expected_queue = None
        if last_dequeued is not None and not (kind == 'reaction_spent' and 'POW-06' in event.get('rules', ())):
            last_dequeued = None
        if boundary is not None and kind not in boundary_events and kind != 'group_turn_boundary':
            issues.append(f'event {seq}: interrupted turn boundary')
        is_standard = (kind in action_events or kind == 'attack' and event.get('reaction') is False
                       or kind == 'shield_activate' and event.get('cost') == 'standard')
        is_reaction = (kind == 'reaction_spent' or kind == 'attack' and event.get('reaction') is True
                       or kind == 'shield_activate' and event.get('cost') == 'reaction')
        if is_standard and (actor not in health or actor != active or event_phase != phase
                            or health[actor] <= 0 or any(x[0] == actor for x in stunned.values())):
            issues.append(f'event {seq}: standard action outside an eligible actor turn')
        if is_reaction and (active is None or event_phase != phase or actor not in health
                            or health[actor] <= 0 or any(x[0] == actor for x in stunned.values())):
            issues.append(f'event {seq}: reaction outside an eligible turn or by incapacitated actor')

        if kind == 'group_turn_boundary':
            if actor not in counts or active is not None or boundary is not None:
                issues.append(f'event {seq}: invalid group turn boundary')
                continue
            counts[actor] += 1
            if event.get('turn_count') != counts[actor]:
                issues.append(f'event {seq}: incorrect actor turn clock')
            boundary = (actor, event_phase)
            due = {token for token, (_, source, deadline) in stunned.items()
                   if source == actor and deadline <= counts[actor]}
            condition_ends = set()
            dodge_due = actor in dodging
        elif kind == 'condition_instance_end' and event.get('condition') == 'stunned':
            token = event.get('instance')
            instance = stunned.get(token)
            if (boundary is None or token not in due or instance is None
                    or actor != instance[0] or event.get('expires_on_actor') != instance[1]):
                issues.append(f'event {seq}: invalid or premature Stunned instance expiration')
            else:
                del stunned[token]
                due.remove(token)
                if not any(item[0] == actor for item in stunned.values()):
                    condition_ends.add(actor)
        elif kind == 'condition_end' and event.get('condition') == 'stunned':
            if boundary is None or actor not in condition_ends:
                issues.append(f'event {seq}: Stunned ended without expiration of every instance')
            else:
                condition_ends.remove(actor)
        elif kind == 'dodge_end':
            if boundary is None or actor != boundary[0] or not dodge_due:
                issues.append(f'event {seq}: Dodge expired at the wrong boundary')
            else:
                dodging.remove(actor)
                dodge_due = False
        elif kind == 'turn_start':
            if boundary != (actor, event_phase) or due or condition_ends or dodge_due:
                issues.append(f'event {seq}: turn began with a missing or invalid condition expiration')
            boundary = None
            if actor not in health or active is not None:
                issues.append(f'event {seq}: invalid or nested actor turn')
                continue
            active, phase = actor, event_phase
            skip_reason = ('dead' if health[actor] <= -maximum[actor] else
                           'unconscious' if health[actor] <= 0 else
                           'stunned' if any(x[0] == actor for x in stunned.values()) else None)
            skip_seen = False
        elif kind == 'turn_skipped':
            if actor != active or event_phase != phase or event.get('reason') != skip_reason or skip_seen:
                issues.append(f'event {seq}: invalid turn skip')
            skip_seen = True
        elif kind == 'turn_end':
            if actor != active or event_phase != phase or bool(skip_reason) != skip_seen:
                issues.append(f'event {seq}: turn end or skipped-action state mismatch')
            if pending:
                issues.append(f'event {seq}: turn ended with unresolved reaction triggers')
            active = phase = None
        elif kind == 'dodge' and actor in health:
            dodging.add(actor)
        elif kind == 'condition_start' and event.get('condition') == 'stunned':
            source, token, deadline = (event.get('expires_on_actor'), event.get('instance'),
                                       event.get('source_turn_count'))
            if (actor not in counts or source not in counts or actor == source
                    or type(deadline) is not int or deadline != counts[source] + 1
                    or token != f'stunned:{names.index(source)}:{names.index(actor)}'):
                issues.append(f'event {seq}: invalid Stunned source, identity or deadline')
            else:
                stunned[token] = (actor, source, deadline)
        elif kind == 'group_hit_check':
            trigger = event.get('trigger')
            if (any(type(event.get(key)) is not int for key in
                    ('modifier', 'target_number', 'edges', 'troubles', 'total'))
                    or any(type(event.get(key)) is not bool for key in
                           ('success', 'fantastic', 'ultimate'))):
                issues.append(f'event {seq}: invalid group hit check field types')
            if type(trigger) is not int or trigger in checks or actor not in health or event.get('target') not in health:
                issues.append(f'event {seq}: invalid or duplicate group hit check')
            else:
                checks[trigger] = event
        elif kind == 'shield_activate' and event.get('cost') == 'reaction' and event.get('timing') != 'end_turn':
            check = checks.get(event.get('trigger'))
            if check is None or check.get('target') != actor or check.get('success') is not True:
                issues.append(f'event {seq}: Shield reaction lacks a successful hit against its owner')
        elif kind == 'attack':
            trigger = event.get('trigger')
            check = checks.get(trigger)
            fields = ('actor', 'target', 'roll', 'rerolls', 'target_number', 'edges', 'troubles',
                      'total', 'success', 'fantastic', 'ultimate')
            if (check is None or any(event.get(key) != check.get(key) for key in fields)
                    or event.get('check_modifier') != check.get('modifier')):
                issues.append(f'event {seq}: attack differs from its pre-damage hit check')
            if trigger in attacks:
                issues.append(f'event {seq}: attack reused a trigger')
            attacks[trigger] = event
            if event.get('success') is False and event.get('mode') != 'ranged':
                expected_queue = (event.get('target'), actor, trigger)
            if event.get('target') in health:
                health[event['target']] = event.get('health_after')
        elif kind == 'reaction_queued':
            trigger = event.get('trigger')
            attack = attacks.get(trigger)
            if (attack is None or attack.get('success') is not False
                    or attack.get('target') != actor or attack.get('actor') != event.get('source')
                    or expected_queue != (actor, event.get('source'), trigger)):
                issues.append(f'event {seq}: invalid reaction queue source')
            else:
                item = (actor, event.get('source'), trigger)
                (pending.appendleft if attack.get('reaction') is True else pending.append)(item)
            expected_queue = None
        elif kind == 'group_reaction_dequeued':
            item = (actor, event.get('source'), event.get('trigger'))
            if (active is None or event_phase != phase or not pending
                    or item != pending[0] or event.get('reaction_kind') != 'riposte'):
                issues.append(f'event {seq}: reaction trigger processed in wrong order')
            if pending:
                pending.popleft()
            last_dequeued = item
        elif kind == 'reaction_spent' and 'POW-06' in event.get('rules', ()):
            if last_dequeued is None or (actor, event.get('trigger')) != (last_dequeued[0], last_dequeued[2]):
                issues.append(f'event {seq}: Riposte did not consume the processed trigger')
            last_dequeued = None
        elif kind in ('heal', 'condition_tick') and actor in health:
            health[actor] = event.get('health_after')
    if active is not None or boundary is not None or pending or expected_queue is not None:
        issues.append('group trace ends with an open turn, boundary or reaction queue')
    if set(checks) != set(attacks):
        issues.append('group hit checks and attacks have different triggers')
    return issues
