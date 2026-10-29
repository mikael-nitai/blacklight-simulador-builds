"""Independent Prone event/attack audit for the experimental duel host."""


def audit_prone_log(log, profiles, *, initial_prone, initial_distance, stack_stunned_edge=False,
                    verified_extra_troubles=None):
    """Reconstruct standing costs and Prone modifiers; use base audits separately."""
    profiles = tuple(profiles)
    if (len(profiles) != 2 or profiles[0].name == profiles[1].name
            or not isinstance(initial_prone, tuple) or len(initial_prone) != 2
            or any(type(value) is not bool for value in initial_prone)
            or type(initial_distance) is not int or initial_distance < 1
            or type(stack_stunned_edge) is not bool):
        raise ValueError('Invalid Prone audit setup')
    if not isinstance(log, (list, tuple)) or any(not isinstance(event, dict) for event in log):
        return ['Invalid Prone log']
    if verified_extra_troubles is None:
        verified_extra_troubles = {}
    if (not isinstance(verified_extra_troubles, dict)
            or any(type(key) is not int or key < 1 or type(value) is not int or value < 0
                   for key, value in verified_extra_troubles.items())):
        raise ValueError('Invalid externally verified trouble contributions')
    names = {profile.name: profile for profile in profiles}
    prone = {profile.name: flag for profile, flag in zip(profiles, initial_prone)}
    stunned = dict.fromkeys(names, False)
    dodging = dict.fromkeys(names, False)
    issues, checks, used = [], {}, set()
    prefix = [profile.name for profile, flag in zip(profiles, initial_prone) if flag]
    for index, name in enumerate(prefix):
        if (index >= len(log) or log[index].get('type') != 'prone_initial'
                or log[index].get('actor') != name):
            issues.append(f'Missing initial Prone marker for {name}')
    distance, pending_stand, pending_start = initial_distance, None, None
    for index, event in enumerate(log):
        kind, actor, target, seq = event.get('type'), event.get('actor'), event.get('target'), event.get('seq')
        if (actor is not None and not isinstance(actor, str)
                or target is not None and not isinstance(target, str)):
            issues.append(f'event {seq}: invalid actor or target')
            continue
        expected_start = pending_start
        if expected_start is not None:
            if (kind != 'prone_start' or (actor, event.get('source'), event.get('trigger')) != expected_start):
                issues.append(f'event {seq}: missing or invalid Prone application after Ram')
            pending_start = None
        if index < len(prefix) and kind == 'prone_initial':
            continue
        if kind == 'prone_initial':
            issues.append(f'event {seq}: unexpected initial Prone marker')
            continue
        if pending_stand is not None:
            name, as_standard, speed = pending_stand
            if (kind != 'movement' or actor != name or event.get('as_standard') is not as_standard
                    or type(event.get('steps')) is not int or not 0 <= event['steps'] <= speed - 1):
                issues.append(f'event {seq}: standing is not paired with a valid movement budget')
            pending_stand = None
        if kind == 'prone_stand':
            if (actor not in names or not prone.get(actor) or event.get('cost') != 1
                    or type(event.get('cost')) is not int or type(event.get('as_standard')) is not bool
                    or type(event.get('speed')) is not int or event['speed'] != names[actor].run_speed
                    or event['speed'] < 1):
                issues.append(f'event {seq}: invalid Prone standing')
            else:
                prone[actor] = False
                pending_stand = (actor, event['as_standard'], event['speed'])
        elif kind == 'prone_start':
            if (expected_start is None or actor not in prone or prone[actor]
                    or (actor, event.get('source'), event.get('trigger')) != expected_start):
                issues.append(f'event {seq}: invalid Prone application')
            else:
                prone[actor] = True
        elif kind == 'movement':
            if actor in prone and prone[actor] and event.get('steps') != 0:
                issues.append(f'event {seq}: unsupported movement while Prone')
            distance = event.get('distance_after')
        elif kind == 'dodge' and actor in dodging:
            dodging[actor] = True
        elif kind == 'dodge_end' and actor in dodging:
            dodging[actor] = False
        elif kind == 'condition_start' and actor in stunned and event.get('condition') == 'stunned':
            stunned[actor] = True
        elif kind == 'condition_end' and actor in stunned and event.get('condition') == 'stunned':
            stunned[actor] = False
        elif kind == 'prone_check':
            mode, trigger = event.get('mode'), event.get('trigger')
            if (actor not in names or target not in names or actor == target
                    or not isinstance(mode, str) or mode not in
                    ('melee', 'ranged', 'fast_strikes', 'blade', 'blade_fast', 'claw',
                     'claw_fast', 'hammer', 'hammer_fast')
                    or type(trigger) is not int or trigger < 1 or trigger in checks):
                issues.append(f'event {seq}: invalid Prone check context')
                continue
            ranged = mode == 'ranged'
            fast = mode == 'fast_strikes' or mode.endswith('_fast')
            added_edges = int(prone[target] and not ranged)
            added_troubles = int(prone[actor] and not ranged) + int(prone[target] and ranged)
            if (not (prone[actor] or prone[target])
                    or type(event.get('attacker_prone')) is not bool
                    or type(event.get('target_prone')) is not bool
                    or event['attacker_prone'] is not prone[actor] or event['target_prone'] is not prone[target]
                    or type(event.get('added_edges')) is not int or event['added_edges'] != added_edges
                    or type(event.get('added_troubles')) is not int or event['added_troubles'] != added_troubles):
                issues.append(f'event {seq}: Prone modifier context mismatch')
            power_edges = 0 if ranged else int('blazing_fast_fists' in names[actor].powers)
            if fast and 'signature_fast_strikes' in names[actor].traits:
                power_edges += 1
            edges = power_edges
            if stunned[target]:
                edges = edges + 1 if stack_stunned_edge else max(1, edges)
            troubles = int(ranged and type(distance) is int and distance > names[actor].ranged_range)
            troubles += int(dodging[target])
            checks[trigger] = (actor, target, mode, edges + added_edges,
                               troubles + added_troubles + verified_extra_troubles.get(trigger, 0))
        elif kind in ('attack', 'fast_limb_check', 'ram_attack'):
            trigger = event.get('trigger')
            if type(trigger) is not int or trigger < 1:
                issues.append(f'event {seq}: invalid attack trigger')
                continue
            mode = event.get('mode') if kind in ('attack', 'ram_attack') else (
                'fast_strikes' if event.get('weapon') == 'bare' else f"{event.get('weapon')}_fast")
            if actor in prone and target in prone and (prone[actor] or prone[target]):
                if trigger not in checks:
                    issues.append(f'event {seq}: missing Prone check context')
                elif checks[trigger] != (actor, target, mode, event.get('edges'), event.get('troubles')):
                    issues.append(f'event {seq}: Prone check or edge/trouble mismatch')
                elif kind in ('attack', 'ram_attack'):
                    used.add(trigger)
            elif trigger in checks:
                issues.append(f'event {seq}: Prone context attached to an upright attack')
            if kind == 'ram_attack':
                transaction = event.get('transaction')
                parameters = transaction.get('parameters') if isinstance(transaction, dict) else None
                if (not isinstance(parameters, dict)
                        or type(parameters.get('fantastic_success')) is not bool):
                    issues.append(f'event {seq}: invalid Ram condition result')
                elif parameters['fantastic_success'] and target in prone and not prone[target]:
                    pending_start = (target, actor, trigger)
    if pending_stand is not None:
        issues.append('End of log: standing has no movement event')
    if pending_start is not None:
        issues.append('End of log: Ram Prone application is missing')
    if set(checks) != used:
        issues.append('Prone check context has no corresponding attack')
    return issues
