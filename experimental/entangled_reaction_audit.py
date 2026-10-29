"""Check reaction queue order, then delegate hold and physical audits."""

from collections import deque
from dataclasses import replace

from .entangled_attack_audit import audit_entangled_attacks


def audit_entangled_reactions(result, profiles, *, inside_attack_trouble, **context):
    profiles = tuple(profiles)
    names = {p.name for p in profiles}
    if len(profiles) != 2 or len(names) != 2:
        raise ValueError('Two distinct profiles are required')
    log = result.log
    if not isinstance(log, (tuple, list)) or any(not isinstance(e, dict) for e in log):
        return ['Invalid entangled reaction trace']
    attacks, queued, used = {}, deque(), set()
    projection, issues = [], []
    for index, event in enumerate(log):
        kind, actor, seq = event.get('type'), event.get('actor'), event.get('seq')
        if type(seq) is not int or seq != index + 1:
            issues.append(f'event {seq}: invalid original sequence')
        if kind in ('attack', 'ram_attack'):
            trigger = event.get('trigger')
            if type(trigger) is int:
                attacks[trigger] = event
        elif kind == 'reaction_queued':
            trigger, source = event.get('trigger'), event.get('source')
            attack = attacks.get(trigger)
            if (type(trigger) is not int or trigger < 1 or trigger in used or attack is None
                    or actor not in names or source not in names or actor == source
                    or attack.get('actor') != source or attack.get('target') != actor):
                issues.append(f'event {seq}: invalid or repeated queued reaction')
            else:
                item = (actor, source, trigger, 'riposte')
                if attack.get('reaction') is True:
                    queued.appendleft(item)
                else:
                    queued.append(item)
                used.add(trigger)
        elif kind == 'entangled_reaction_dequeued':
            item = (actor, event.get('source'), event.get('trigger'), event.get('reaction_kind'))
            if not queued or queued.popleft() != item:
                issues.append(f'event {seq}: reaction processed out of order')
            continue
        copy = dict(event)
        copy['seq'] = len(projection) + 1
        projection.append(copy)
    if queued:
        issues.append('Unprocessed reaction queue at the end of the duel')
    if issues:
        return issues
    return audit_entangled_attacks(replace(result, log=tuple(projection)), profiles,
        inside_attack_trouble=inside_attack_trouble, allow_reaction_ranged=True,
        nested_reactions_first=True, **context)
