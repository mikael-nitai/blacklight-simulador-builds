"""Experimental group initiative verifier, independent of its ordering resolver."""

from blacklight.dice_audit import audit_rerolls


def audit_group_initiative(log, profiles, roles, tie_order):
    names = tuple(profile.name for profile in profiles)
    n = len(names)
    if (n < 2 or len(set(names)) != n or not isinstance(roles, tuple)
            or len(roles) != n or any(role not in ('player', 'npc') for role in roles)
            or tie_order is not None and
            (not isinstance(tie_order, tuple) or len(tie_order) != n
             or any(type(i) is not int for i in tie_order) or set(tie_order) != set(range(n)))):
        raise ValueError('Audit requires roster roles and a valid optional tie order')
    rows, declarations, turns, issues = {}, [], [], []
    for event in log:
        kind = event.get('type')
        if kind == 'initiative':
            if declarations or turns:
                issues.append('initiative roll after order declaration or turn')
            name = event.get('actor')
            if name not in names or name in rows:
                issues.append('invalid or repeated initiative actor')
                continue
            i = names.index(name)
            profile = profiles[i]
            modifier = profile.initiative_modifier if profile.initiative_modifier is not None else profile.vigilance
            issues.extend(audit_rerolls(event, edges=int('situational_awareness' in profile.traits), troubles=0))
            dice = event.get('roll')
            if (not isinstance(dice, (tuple, list)) or len(dice) != 3
                    or any(type(face) is not int or not 1 <= face <= 6 for face in dice)):
                issues.append('invalid initiative dice')
                continue
            total = dice[0] + (6 if dice[1] == 1 else dice[1]) + dice[2] + modifier
            fantastic = dice[1] == 1
            if (event.get('modifier') != modifier or event.get('total') != total
                    or type(event.get('fantastic')) is not bool or event['fantastic'] != fantastic):
                issues.append('initiative does not match profile and dice')
            rows[name] = (total, fantastic, modifier)
        elif kind == 'group_initiative_order':
            if len(rows) != n or turns:
                issues.append('initiative order declared outside its scheduling window')
            declarations.append(event)
        elif kind == 'turn_start':
            if len(declarations) != 1:
                issues.append('turn began before unique initiative declaration')
            turns.append(event)
    if len(rows) != n or len(declarations) != 1:
        return issues + ['missing initiative or unique group order declaration']
    keys = [(-rows[name][0], -int(rows[name][1]), -rows[name][2],
             0 if roles[i] == 'player' else 1) for i, name in enumerate(names)]
    if len(set(keys)) != n and tie_order is None:
        return issues + ['undeclared unresolved initiative tie']
    priority = {index: rank for rank, index in enumerate(tie_order or tuple(range(n)))}
    expected = sorted(range(n), key=lambda i: (*keys[i], priority[i]))
    declaration = declarations[0]
    if (declaration.get('roles') != list(roles)
            or declaration.get('tie_order') != (list(tie_order) if tie_order else None)
            or declaration.get('order') != expected):
        issues.append('declared initiative order or input differs from evidence')
    phase_turns = {}
    last = None
    for event in turns:
        phase = (event.get('round'), event.get('bonus_round'))
        if (type(phase[0]) is not int or type(phase[1]) is not bool
                or phase[0] < 0 or phase[1] != (phase[0] == 0)):
            issues.append('invalid initiative phase')
            continue
        available = [names[i] for i in expected if not phase[1] or rows[names[i]][1]]
        if last is None:
            first = (0, True) if any(row[1] for row in rows.values()) else (1, False)
            if phase != first:
                issues.append('first turn phase does not follow initiative')
        if last is not None and phase != last:
            previous = [names[i] for i in expected if not last[1] or rows[names[i]][1]]
            if phase[0] != last[0] + 1 or phase_turns[last] != previous:
                issues.append('initiative phase changed before scheduled turns completed')
        current = phase_turns.setdefault(phase, [])
        if len(current) >= len(available) or event.get('actor') != available[len(current)]:
            issues.append('turn order differs from declared initiative')
        current.append(event.get('actor'))
        last = phase
    return issues
