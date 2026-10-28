"""Reconstruct the open-field distance without calling movement code."""


def audit_open_field_distance(log, initial_distance):
    if type(initial_distance) is not int or initial_distance < 1:
        raise ValueError('Open-field audit requires a positive initial distance')
    distance, issues = initial_distance, []
    for event in log:
        kind, seq = event.get('type'), event.get('seq')
        if kind == 'movement':
            direction, steps = event.get('direction'), event.get('steps')
            if (type(steps) is not int or steps < 0
                    or direction not in ('stay', 'approach', 'retreat')
                    or direction == 'stay' and steps != 0):
                issues.append(f'event {seq}: invalid movement for distance audit')
                continue
            expected = (max(1, distance - steps) if direction == 'approach' else
                        distance + steps if direction == 'retreat' else distance)
            if event.get('distance_before') != distance or event.get('distance_after') != expected:
                issues.append(f'event {seq}: open-field distance ledger mismatch')
            distance = expected
        elif kind == 'knockback':
            spaces = event.get('spaces')
            if type(spaces) is not int or spaces < 1:
                issues.append(f'event {seq}: invalid knockback distance')
                continue
            expected = distance + spaces
            if event.get('distance_before') != distance or event.get('distance_after') != expected:
                issues.append(f'event {seq}: knockback distance ledger mismatch')
            distance = expected
        elif kind == 'attack' and event.get('distance') != distance:
            issues.append(f'event {seq}: attack distance differs from movement ledger')
    return issues
