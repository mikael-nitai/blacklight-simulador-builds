"""Independently check attacks during a hold and their added trouble."""

from dataclasses import replace

from .grappling_duel_audit import audit_grappling_duel


def audit_entangled_attacks(result, profiles, *, inside_attack_trouble, **context):
    profiles = tuple(profiles)
    names = {p.name for p in profiles}
    if len(profiles) != 2 or len(names) != 2 or type(inside_attack_trouble) is not bool:
        raise ValueError('Invalid entangled attack audit context')
    holder, victim, pinned = None, None, False
    pending, extras, projection, issues = {}, {}, [], []
    for index, event in enumerate(result.log):
        kind, actor, target, seq = (event.get('type'), event.get('actor'),
                                     event.get('target'), event.get('seq'))
        if type(seq) is not int or seq != index + 1:
            issues.append(f'event {seq}: invalid original sequence')
        if kind == 'grapple_end':
            tx = event.get('transaction')
            if isinstance(tx, dict) and tx.get('attack_success') is True:
                holder, victim, pinned = actor, target, tx.get('fantastic_success')
        elif kind == 'grapple_escape':
            tx = event.get('transaction')
            if isinstance(tx, dict) and tx.get('success') is True:
                holder, victim, pinned = None, None, False
        elif kind == 'grapple_release':
            holder, victim, pinned = None, None, False
        elif kind == 'entangled_attack_check':
            trigger = event.get('trigger')
            expected_pinned = bool(pinned and actor == victim)
            amount = int(expected_pinned) + int(inside_attack_trouble)
            if (holder is None or actor not in (holder, victim) or target not in (holder, victim)
                    or actor == target or type(trigger) is not int or trigger < 1 or trigger in extras
                    or event.get('mode') == 'ranged' or not isinstance(event.get('mode'), str)
                    or type(event.get('pinned')) is not bool or event['pinned'] is not expected_pinned
                    or type(event.get('inside_attack_trouble')) is not bool
                    or event['inside_attack_trouble'] is not inside_attack_trouble
                    or type(event.get('added_troubles')) is not int or event['added_troubles'] != amount):
                issues.append(f'event {seq}: invalid entangled attack modifier')
            if type(trigger) is int:
                pending[trigger] = (actor, target, event.get('mode'))
                extras[trigger] = amount
            continue
        elif kind == 'attack':
            trigger = event.get('trigger')
            if holder is not None:
                if pending.pop(trigger, None) != (actor, target, event.get('mode')):
                    issues.append(f'event {seq}: missing entangled attack check')
                if event.get('knockback_selected') is not False:
                    issues.append(f'event {seq}: entangled knockback is unsupported')
            elif trigger in pending:
                issues.append(f'event {seq}: attack occurred after hold ended')
        copy = dict(event)
        copy['seq'] = len(projection) + 1
        projection.append(copy)
    if pending:
        issues.append('Unresolved entangled attack checks')
    if issues:
        return issues
    return audit_grappling_duel(replace(result, log=tuple(projection)), profiles,
        allow_entangled_attacks=True, entangled_verified_troubles=extras, **context)
