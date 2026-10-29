"""Audit single-target submachine checks before delegating to other ledgers."""

from dataclasses import replace
from .ranged_powers_audit import audit_ranged_powers_duel


def audit_submachine_duel(result, profiles, *, ranged_weapons, **context):
    profiles = tuple(profiles)
    if (len(profiles) != 2 or len({p.name for p in profiles}) != 2
            or not isinstance(ranged_weapons, tuple) or len(ranged_weapons) != 2
            or any(weapon not in ('generic', 'submachine_gun') for weapon in ranged_weapons)):
        raise ValueError('Two profiles and explicit ranged weapons are required')
    names = {p.name: (p, weapon) for p, weapon in zip(profiles, ranged_weapons)}
    for p, weapon in zip(profiles, ranged_weapons):
        if weapon == 'submachine_gun' and (p.ranged_range != 10 or not p.ranged_is_ammunition
                                            or p.ranged_bonus < 1):
            raise ValueError('Invalid submachine gun profile')
    issues, pending, extra = [], None, {}
    for event in result.log:
        kind, actor, seq = event.get('type'), event.get('actor'), event.get('seq')
        if pending is not None and kind not in ('prone_check', 'shield_deactivate',
                                                'reaction_spent', 'shield_activate', 'attack'):
            issues.append(f'event {seq}: submachine check has no matching attack')
            pending = None
        if kind == 'smg_close_check':
            trigger, target, distance = event.get('trigger'), event.get('target'), event.get('distance')
            if (pending is not None or actor not in names or names[actor][1] != 'submachine_gun'
                    or target not in names or target == actor or type(trigger) is not int or trigger < 1
                    or trigger in extra or type(distance) is not int or not 1 <= distance <= 5
                    or type(event.get('added_troubles')) is not int or event['added_troubles'] != 1):
                issues.append(f'event {seq}: invalid submachine gun close check')
            if type(trigger) is int and trigger > 0:
                extra[trigger] = 1
            pending = (actor, target, trigger, distance)
        elif kind == 'attack':
            if pending is not None:
                if ((actor, event.get('target'), event.get('trigger'), event.get('distance')) != pending
                        or event.get('mode') != 'ranged'):
                    issues.append(f'event {seq}: submachine check does not match attack')
                pending = None
            if actor in names:
                distance = event.get('distance')
                expected = (event.get('mode') == 'ranged' and names[actor][1] == 'submachine_gun'
                            and type(distance) is int and distance <= 5)
                if (event.get('trigger') in extra) is not expected:
                    issues.append(f'event {seq}: missing or spurious submachine close trouble')
    if pending is not None:
        issues.append('Submachine close check has no matching attack')
    if issues:
        return issues
    projection = []
    for event in result.log:
        if event.get('type') == 'smg_close_check':
            continue
        copy = dict(event)
        copy['seq'] = len(projection) + 1
        projection.append(copy)
    return audit_ranged_powers_duel(replace(result, log=tuple(projection)), profiles,
                                    verified_extra_troubles=extra, **context)
