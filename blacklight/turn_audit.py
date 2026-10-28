"""Check complete two-fighter traces against their recorded turn schedule."""


def audit_turn_sequence(log, profiles, *, outcome):
    names = tuple(profile.name for profile in profiles)
    if len(names) != 2 or len(set(names)) != 2:
        raise ValueError('A turn audit needs two distinct profiles')
    initiative = {}
    starts = {}
    active = None
    active_phase = None
    last_phase = None
    issues = []
    turn_actions = {'movement', 'fast_use_start', 'fast_limb_check',
                    'fast_limb_start', 'fast_use_end', 'stance', 'dodge',
                    'focus_spent', 'wait', 'condition_treatment',
                    'blade_bonus', 'turn_skipped'}

    def phase_order(phase):
        round_number, bonus = phase
        return 0 if bonus and round_number == 0 else round_number

    def expected_order(phase):
        if len(initiative) != 2 or any(
                type(initiative[name].get('total')) is not int
                or type(initiative[name].get('modifier')) is not int
                or type(initiative[name].get('fantastic')) is not bool
                for name in names):
            return ()
        order = sorted(names, key=lambda name: (-initiative[name]['total'],
                       -int(initiative[name]['fantastic']),
                       -initiative[name]['modifier'], names.index(name)))
        return tuple(name for name in order if not phase[1] or initiative[name]['fantastic'])

    for event in log:
        kind, actor, seq = event.get('type'), event.get('actor'), event.get('seq')
        phase = (event.get('round'), event.get('bonus_round'))
        if kind == 'initiative':
            if actor not in names or actor in initiative or starts or active is not None:
                issues.append(f'event {seq}: invalid or repeated initiative')
            else:
                initiative[actor] = event
        elif kind == 'turn_start':
            if (actor not in names or active is not None or len(initiative) != 2
                    or type(phase[0]) is not int or type(phase[1]) is not bool
                    or (phase[1] and phase[0] != 0) or (not phase[1] and phase[0] < 1)):
                issues.append(f'event {seq}: invalid turn start or phase')
                continue
            if last_phase is not None and phase != last_phase:
                if phase_order(phase) != phase_order(last_phase) + 1:
                    issues.append(f'event {seq}: nonconsecutive turn phases')
                if len(starts[last_phase]) != len(expected_order(last_phase)):
                    issues.append(f'event {seq}: previous phase ended before all scheduled turns')
            elif last_phase is None:
                first_phase = (0, True) if any(row.get('fantastic') is True
                                                for row in initiative.values()) else (1, False)
                if phase != first_phase:
                    issues.append(f'event {seq}: first phase does not follow initiative')
            order = expected_order(phase)
            current = starts.setdefault(phase, [])
            if len(current) >= len(order) or actor != order[len(current)]:
                issues.append(f'event {seq}: turn order differs from initiative')
            current.append(actor)
            active, active_phase, last_phase = actor, phase, phase
        elif kind == 'turn_end':
            if active is None or actor != active or phase != active_phase:
                issues.append(f'event {seq}: turn end does not match active turn')
            active, active_phase = None, None
        else:
            is_turn_action = (kind in turn_actions
                              or kind == 'attack' and event.get('reaction') is False
                              or kind == 'shield_activate' and event.get('cost') == 'standard')
            is_reaction = (kind in {'reaction_spent', 'reaction_queued'}
                           or kind == 'attack' and event.get('reaction') is True
                           or kind == 'shield_activate' and event.get('cost') == 'reaction')
            if is_turn_action and (active != actor or phase != active_phase):
                issues.append(f'event {seq}: action outside the actor turn')
            if is_reaction and (active is None or actor not in names or phase != active_phase):
                issues.append(f'event {seq}: reaction outside an active turn')

    if len(initiative) != 2:
        issues.append('complete duel must have one initiative per combatant')
    if active is not None:
        issues.append('complete duel ended with an open turn')
    if not starts:
        issues.append('complete duel has no turns')
    elif outcome == 'inconclusive' and len(starts[last_phase]) != len(expected_order(last_phase)):
        issues.append('inconclusive duel ended before all scheduled turns')
    return issues
