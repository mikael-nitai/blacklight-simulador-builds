"""Independent arithmetic and chronology check of the synthetic Ram record."""


def audit_ram_record(record):
    """Return issues; do not call the trigger, impact, or transaction implementation."""
    try:
        if not isinstance(record, dict) or record.get('schema') != 'blacklight-experimental-ram-transaction-v1':
            raise ValueError('schema')
        a, b, before, after, p, impact = (record[key] for key in
                                          ('first', 'second', 'before', 'after', 'parameters', 'impact'))
        if not all(isinstance(item, dict) for item in (a, b, before, after, p, impact)):
            raise ValueError('record shape')
        if record.get('scope') != 'synthetic simultaneous damage; no Heroic, Shield, Riposte or weapon effects':
            raise ValueError('scope')

        def integer(value, minimum=None):
            return type(value) is int and (minimum is None or value >= minimum)

        for segment in (a, b):
            if (any(not isinstance(segment.get(key), str) or not segment[key]
                    for key in ('actor', 'target')) or segment['actor'] == segment['target']
                    or not integer(segment.get('turn'), 1) or not integer(segment.get('speed'), 1)
                    or not integer(segment.get('before'), 1) or not integer(segment.get('after'), 1)
                    or not 0 < segment['before'] - segment['after'] <= segment['speed']):
                raise ValueError('movement segment')
        if (a.get('action') != 'movement' or b.get('action') != 'standard'
                or any(a[key] != b[key] for key in ('actor', 'target', 'turn', 'speed'))
                or a['before'] - a['after'] != a['speed'] or a['after'] != b['before']
                or b['after'] != 1):
            raise ValueError('movement trigger')
        if (not integer(before.get('attacker_health'), 1) or not integer(before.get('target_health'), 1)
                or not integer(before.get('reactions'), 1) or before.get('attacker_able') is not True
                or type(before.get('target_prone')) is not bool):
            raise ValueError('prior state')
        if (type(p.get('success')) is not bool or type(p.get('fantastic_success')) is not bool
                or p['fantastic_success'] and not p['success']
                or not integer(p.get('full_dice'), 0) or not integer(p.get('ability'))
                or not integer(p.get('target_reduction'), 0) or not integer(p.get('attacker_reduction'), 0)
                or p.get('self_pool') not in ('shared', 'separate')
                or set(p) != {'success', 'fantastic_success', 'full_dice', 'ability',
                              'target_reduction', 'attacker_reduction', 'target_faces',
                              'self_pool', 'attacker_faces'}):
            raise ValueError('damage parameters')
        count = p['full_dice'] if p['success'] else 0

        def valid_faces(faces):
            return (isinstance(faces, list) and len(faces) == count
                    and all(integer(face, 1) and face <= 6 for face in faces))

        if not valid_faces(p.get('target_faces')):
            raise ValueError('target faces')
        if p['self_pool'] == 'shared':
            if p.get('attacker_faces') is not None:
                raise ValueError('shared pool')
            own = p['target_faces']
        else:
            own = p.get('attacker_faces')
            if not valid_faces(own):
                raise ValueError('separate pool')

        def manual_regular(faces, reduction):
            if not p['success']:
                return 0
            kept = max(0, p['full_dice'] - reduction)
            if kept == 0:
                return 0
            values = [6 if face == 1 else face for face in faces[:kept]]
            return max(0, sum(values) + p['ability'])

        target = manual_regular(p['target_faces'], p['target_reduction'])
        attacker = manual_regular(own, p['attacker_reduction'])
        target_damage = target * (3 if p['fantastic_success'] else 2)
        expected_impact = {'target_regular': target, 'attacker_regular': attacker,
                           'target_damage': target_damage, 'attacker_damage': attacker,
                           'target_prone': p['fantastic_success']}
        expected_after = {'attacker_health': before['attacker_health'] - attacker,
                          'target_health': before['target_health'] - target_damage,
                          'reactions': before['reactions'] - 1,
                          'attacker_able': before['attacker_health'] - attacker > 0,
                          'target_prone': before['target_prone'] or p['fantastic_success']}
        if (any(not integer(impact.get(key), 0) for key in
                ('target_regular', 'attacker_regular', 'target_damage', 'attacker_damage'))
                or type(impact.get('target_prone')) is not bool
                or any(not integer(after.get(key)) for key in ('attacker_health', 'target_health', 'reactions'))
                or type(after.get('attacker_able')) is not bool or type(after.get('target_prone')) is not bool):
            raise ValueError('recorded value types')
        if impact != expected_impact:
            raise ValueError('impact mismatch')
        if after != expected_after:
            raise ValueError('state mismatch')
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        return [f'Invalid experimental Ram record: {error}']
    return []
