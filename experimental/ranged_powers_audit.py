"""Independent audit for combined Double Tap and Slow-Motion Dodge duels."""

from dataclasses import replace

from .double_tap_audit import audit_double_tap_duel


def audit_ranged_powers_duel(result, profiles, *, initial_prone,
                             verified_extra_troubles=None, **context):
    profiles = tuple(profiles)
    if (len(profiles) != 2 or len({p.name for p in profiles}) != 2
            or not isinstance(initial_prone, tuple) or len(initial_prone) != 2
            or any(type(flag) is not bool for flag in initial_prone)):
        raise ValueError('Two distinct profiles and their initial Prone state are required')
    names = {p.name: p for p in profiles}
    if verified_extra_troubles is None:
        verified_extra_troubles = {}
    if (not isinstance(verified_extra_troubles, dict)
            or any(type(k) is not int or k < 1 or type(v) is not int or v < 0
                   for k, v in verified_extra_troubles.items())):
        raise ValueError('Invalid externally verified trouble contributions')
    prone = {p.name: flag for p, flag in zip(profiles, initial_prone)}
    dodging = dict.fromkeys(names, False)
    stunned = dict.fromkeys(names, False)
    health = {p.name: p.max_health for p in profiles}
    issues, pending, triggers = [], None, {}
    log = result.log
    for index, event in enumerate(log):
        kind, actor, target, seq = (event.get('type'), event.get('actor'),
                                    event.get('target'), event.get('seq'))
        if pending is not None and kind not in ('prone_check', 'shield_deactivate',
                                                'reaction_spent', 'shield_activate', 'attack'):
            issues.append(f'event {seq}: Slow-Motion Dodge has no immediate matching attack')
            pending = None
        if kind == 'prone_stand' and actor in prone:
            prone[actor] = False
        elif kind == 'prone_start' and actor in prone:
            prone[actor] = True
        elif kind == 'dodge' and actor in dodging:
            dodging[actor] = True
        elif kind == 'dodge_end' and actor in dodging:
            dodging[actor] = False
        elif kind == 'condition_start' and actor in stunned and event.get('condition') == 'stunned':
            stunned[actor] = True
        elif kind == 'condition_end' and actor in stunned and event.get('condition') == 'stunned':
            stunned[actor] = False
        elif kind == 'slow_motion_dodge':
            prev = log[index - 1] if index else {}
            p, trigger = names.get(actor), event.get('trigger')
            if (pending is not None or p is None or actor == event.get('attacker')
                    or event.get('attacker') not in names or 'slow_motion_dodge' not in p.powers
                    or 'brawling' in p.powers or not (type(health.get(actor)) is int and health[actor] > 0)
                    or stunned.get(actor) or type(trigger) is not int or trigger < 1 or trigger in triggers
                    or prev.get('type') != 'reaction_spent' or prev.get('source') != 'slow_motion_dodge'
                    or prev.get('actor') != actor or prev.get('trigger') != trigger
                    or event.get('before_roll') is not True
                    or type(event.get('added_troubles')) is not int or event['added_troubles'] != 1):
                issues.append(f'event {seq}: invalid Slow-Motion Dodge')
            if type(trigger) is int and trigger > 0:
                triggers[trigger] = 1
            pending = (actor, event.get('attacker'), trigger)
        elif kind == 'reaction_spent' and event.get('source') == 'slow_motion_dodge':
            after = log[index + 1] if index + 1 < len(log) else {}
            if (after.get('type') != 'slow_motion_dodge' or after.get('actor') != actor
                    or after.get('trigger') != event.get('trigger')):
                issues.append(f'event {seq}: missing Slow-Motion Dodge marker')
        elif kind == 'attack':
            if pending is not None:
                if (event.get('mode') != 'ranged' or (target, actor, event.get('trigger')) != pending):
                    issues.append(f'event {seq}: Slow-Motion Dodge attack mismatch')
                pending = None
            p, q = names.get(actor), names.get(target)
            if p is not None and q is not None:
                ranged = event.get('mode') == 'ranged'
                distance = event.get('distance')
                expected = int(dodging[target]) + int(prone[actor] and not ranged)
                expected += int(prone[target] and ranged)
                if ranged and type(distance) is int:
                    expected += int(distance > p.ranged_range)
                expected += triggers.get(event.get('trigger'), 0)
                expected += verified_extra_troubles.get(event.get('trigger'), 0)
                if type(event.get('troubles')) is not int or event['troubles'] != expected:
                    issues.append(f'event {seq}: combined attack trouble mismatch')
                health[target] = event.get('health_after')
        elif kind == 'ram_attack' and actor in names and target in names:
            health[actor], health[target] = event.get('attacker_health_after'), event.get('target_health_after')
        elif kind in ('heal', 'condition_tick') and actor in names:
            health[actor] = event.get('health_after')
    if pending is not None:
        issues.append('Slow-Motion Dodge has no matching attack')
    if issues:
        return issues
    # Preserve the real rerolls and trouble counts. The Prone auditor receives
    # only independently verified extra sources; remove framing markers in a
    # temporary projection understood by the older combined auditors.
    projection = []
    for event in log:
        if event.get('type') == 'slow_motion_dodge':
            continue
        copy = dict(event)
        copy['seq'] = len(projection) + 1
        projection.append(copy)
    combined = dict(verified_extra_troubles)
    for trigger, trouble in triggers.items():
        combined[trigger] = combined.get(trigger, 0) + trouble
    return audit_double_tap_duel(replace(result, log=tuple(projection)), profiles,
                                 initial_prone=initial_prone,
                                 verified_extra_troubles=combined, **context)
