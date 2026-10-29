"""Independently check the table's stop-before-healing Ram ruling."""


def audit_ram_stop(log, profiles, *, stop_on_attacker):
    profiles = tuple(profiles)
    names = {p.name: p for p in profiles}
    issues, expected = [], None
    if (len(profiles) != 2 or len(names) != 2 or not isinstance(stop_on_attacker, str)
            or stop_on_attacker not in names):
        raise ValueError('Two distinct profiles are required')
    for index, event in enumerate(log):
        kind, actor, seq = event.get('type'), event.get('actor'), event.get('seq')
        if expected is not None:
            if kind == 'prone_start' and expected['allow_prone']:
                if (actor != expected['target'] or event.get('source') != expected['actor']
                        or event.get('trigger') != expected['trigger']):
                    issues.append(f'event {seq}: invalid Prone after incapacitating Ram')
                expected['allow_prone'] = False
                continue
            if (kind != 'ram_incapacity_stop' or actor != expected['actor']
                    or event.get('target') != expected['target']
                    or event.get('trigger') != expected['trigger']
                    or type(event.get('health')) is not int or event['health'] != expected['health']
                    or event.get('reason') != 'combat_ends_before_recovery'):
                issues.append(f'event {seq}: missing or invalid Ram stop marker')
            following = log[index + 1] if index + 1 < len(log) else {}
            if (following.get('type') != 'turn_end' or following.get('actor') != expected['actor']
                    or index + 2 != len(log)):
                issues.append(f'event {seq}: combat continued after Ram self-incapacitation')
            expected = None
            continue
        if kind == 'ram_incapacity_stop':
            issues.append(f'event {seq}: stop marker without self-incapacitating Ram')
        if kind != 'ram_attack' or actor not in names:
            continue
        hp = event.get('attacker_health_after')
        if type(hp) is not int:
            issues.append(f'event {seq}: invalid attacker Health')
        elif hp <= -names[actor].max_health:
            issues.append(f'event {seq}: unresolved death threshold must abort the duel')
        elif hp <= 0:
            if actor != stop_on_attacker:
                issues.append(f'event {seq}: self-incapacitation of another attacker is unresolved')
            transaction = event.get('transaction')
            params = transaction.get('parameters') if isinstance(transaction, dict) else None
            if not isinstance(params, dict):
                issues.append(f'event {seq}: missing Ram parameters')
                continue
            expected = {'actor': actor, 'target': event.get('target'), 'trigger': event.get('trigger'),
                        'health': hp, 'allow_prone': params.get('fantastic_success') is True}
    if expected is not None:
        issues.append('Self-incapacitating Ram has no stop marker')
    return issues
