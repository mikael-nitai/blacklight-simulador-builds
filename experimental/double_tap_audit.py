"""Independent validation of Double Tap plus the existing full duel ledgers."""

from dataclasses import replace
from .nonlethal_ram_audit import audit_nonlethal_ram_duel


def audit_double_tap_duel(result, profiles, **context):
    profiles = tuple(profiles)
    if len(profiles) != 2 or len({profile.name for profile in profiles}) != 2:
        raise ValueError('Exactly two distinct profiles are required')
    names = {profile.name: profile for profile in profiles}
    issues, pending = [], None
    log = result.log
    for event in log:
        kind, actor, seq = event.get('type'), event.get('actor'), event.get('seq')
        if kind == 'double_tap_start':
            target, distance = event.get('target'), event.get('distance')
            p = names.get(actor)
            if (pending is not None or p is None or target not in names or target == actor
                    or 'double_tap' not in p.powers or p.ranged_range < 1
                    or type(distance) is not int or not 1 <= distance <= min(2, 2 * p.ranged_range)):
                issues.append(f'event {seq}: illegal Double Tap start')
            pending = {'actor': actor, 'target': target, 'distance': distance,
                       'attack': None, 'condition': None}
        elif kind == 'attack' and pending is not None:
            if (pending['attack'] is not None or actor != pending['actor']
                    or event.get('target') != pending['target'] or event.get('mode') != 'ranged'
                    or event.get('distance') != pending['distance'] or event.get('reaction') is not False):
                issues.append(f'event {seq}: Double Tap attack does not match declaration')
            pending['attack'] = event
        elif (kind == 'condition_start' and 'CORE-P95-DOUBLE-TAP' in event.get('rules', ())):
            attack = pending.get('attack') if pending is not None else None
            if (attack is None or pending['condition'] is not None
                    or actor != pending['target'] or event.get('condition') != 'bleeding'
                    or type(event.get('intensity')) is not int or event['intensity'] != 5
                    or event.get('trigger') != attack.get('trigger')):
                issues.append(f'event {seq}: invalid Double Tap bleeding')
            if pending is not None:
                pending['condition'] = event
        elif kind == 'double_tap_end':
            attack = pending.get('attack') if pending is not None else None
            if attack is None:
                issues.append(f'event {seq}: Double Tap has no matching attack')
            else:
                expected = (attack.get('success') is True and attack.get('fantastic') is True
                            and attack.get('ammunition_immunity') is False)
                if (actor != pending['actor'] or event.get('target') != pending['target']
                        or event.get('trigger') != attack.get('trigger')
                        or type(event.get('bleeding')) is not bool or event['bleeding'] is not expected
                        or (pending['condition'] is not None) is not expected):
                    issues.append(f'event {seq}: Double Tap result or bleeding mismatch')
            pending = None
        elif pending is not None:
            allowed = {'prone_check', 'reaction_spent', 'shield_activate', 'shield_deactivate'}
            queued_miss = (context.get('allow_experimental_parry') is True
                           and kind == 'reaction_queued' and pending['attack'] is not None
                           and pending['attack'].get('success') is False
                           and event.get('trigger') == pending['attack'].get('trigger')
                           and actor == pending['target'] and event.get('source') == pending['actor'])
            if not queued_miss and (pending['attack'] is not None or kind not in allowed):
                issues.append(f'event {seq}: unexpected event during Double Tap')
    if pending is not None:
        issues.append('Double Tap declaration has no completion')
    if issues:
        return issues
    # The existing auditors understand the ordinary ranged attack and the
    # bleeding condition; validate the added transaction above, then remove
    # only its framing markers from a copy used as input to those auditors.
    projection = []
    for event in log:
        if event.get('type') in ('double_tap_start', 'double_tap_end'):
            continue
        copy = dict(event)
        copy['seq'] = len(projection) + 1
        projection.append(copy)
    projected = replace(result, log=tuple(projection))
    return audit_nonlethal_ram_duel(projected, profiles, **context)
