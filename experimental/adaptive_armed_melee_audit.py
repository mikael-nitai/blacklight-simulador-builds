"""Audit declared lethality before delegating to independent combat auditors."""

from dataclasses import replace

from .stopping_audit import audit_stopping_duel


def audit_declared_armed_melee(result, profiles, *, declared_armed_lethal, **context):
    profiles = tuple(profiles)
    names = {p.name: p for p in profiles}
    if (len(profiles) != 2 or len(names) != 2 or not isinstance(declared_armed_lethal, tuple)
            or any(not isinstance(name, str) or name not in names or names[name].heroic
                   or not (names[name].weapons or names[name].ranged_range)
                   for name in declared_armed_lethal)
            or len(set(declared_armed_lethal)) != len(declared_armed_lethal)):
        raise ValueError('Invalid declared armed melee audit contract')
    pending = None
    projection = []
    issues = []
    for index, event in enumerate(result.log):
        kind, actor, target, seq = (event.get('type'), event.get('actor'),
                                     event.get('target'), event.get('seq'))
        if type(seq) is not int or seq != index + 1:
            issues.append(f'event {seq}: invalid original sequence')
        if kind == 'lethality_declaration':
            if (pending is not None or actor not in declared_armed_lethal or target not in names
                    or actor == target or event.get('mode') != 'melee' or event.get('choice') != 'lethal'):
                issues.append(f'event {seq}: invalid lethal declaration')
            pending = (actor, target)
            continue
        if pending is not None and kind not in ('attack', 'prone_check', 'shield_deactivate',
                                                'reaction_spent', 'shield_activate'):
            issues.append(f'event {seq}: lethal declaration interrupted before the attack')
        if kind == 'attack':
            profile = names.get(actor)
            armed_bare = (profile is not None and not profile.heroic
                          and bool(profile.weapons or profile.ranged_range)
                          and event.get('mode') == 'melee' and event.get('offhand') is None)
            if armed_bare:
                if (pending != (actor, target) or actor not in declared_armed_lethal
                        or event.get('declared_lethality') != 'lethal'):
                    issues.append(f'event {seq}: armed bare attack lacks a prior lethal declaration')
                pending = None
            elif pending is not None or 'declared_lethality' in event:
                issues.append(f'event {seq}: unexpected declaration or marked attack')
        copied = dict(event)
        copied['seq'] = len(projection) + 1
        projection.append(copied)
    if pending is not None:
        issues.append('Lethal declaration has no matching attack')
    if issues:
        return issues
    return audit_stopping_duel(replace(result, log=tuple(projection)), profiles,
                               declared_armed_lethal=declared_armed_lethal, **context)
