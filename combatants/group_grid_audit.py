"""Independent position, movement, range and conservative sight ledger."""


def audit_group_grid(log, profiles, *, width, height, initial_positions, final_positions):
    names = tuple(profile.name for profile in profiles)
    n = len(names)
    def valid_point(point):
        return (isinstance(point, (tuple, list)) and len(point) == 2
                and all(type(value) is int for value in point)
                and 0 <= point[0] < width and 0 <= point[1] < height)
    if (type(width) is not int or type(height) is not int or width < 1 or height < 1
            or len(set(names)) != n or n < 2 or len(initial_positions) != n
            or len(final_positions) != n or any(not valid_point(p) for p in initial_positions)
            or any(not valid_point(p) for p in final_positions)
            or len({tuple(p) for p in initial_positions}) != n
            or len({tuple(p) for p in final_positions}) != n):
        raise ValueError('Invalid independent grid audit inputs')
    positions = {name: tuple(point) for name, point in zip(names, initial_positions)}
    by_name = {profile.name: profile for profile in profiles}
    attacks = {event.get('trigger'): event for event in log if event.get('type') == 'attack'}
    dodging = set()
    movement_seen = set()
    open_fast = False
    issues = []
    for event in log:
        kind, actor, seq = event.get('type'), event.get('actor'), event.get('seq')
        if kind == 'fast_use_start':
            open_fast = True
        elif kind == 'fast_use_end':
            open_fast = False
        elif kind == 'dodge':
            dodging.add(actor)
        elif kind == 'dodge_end':
            dodging.discard(actor)
        elif kind == 'group_grid_move':
            if actor not in positions:
                issues.append(f'event {seq}: unknown grid movement actor')
                continue
            key = (actor, event.get('round'), event.get('bonus_round'))
            if key in movement_seen or open_fast:
                issues.append(f'event {seq}: repeated movement or movement during Fast resolution')
            movement_seen.add(key)
            origin = positions[actor]
            path = event.get('path')
            if (not isinstance(path, list) or any(not valid_point(point) for point in path)
                    or type(event.get('steps')) is not int or event['steps'] != len(path)
                    or len(path) > by_name[actor].run_speed or event.get('as_standard') is not False
                    or not valid_point(event.get('origin')) or not valid_point(event.get('destination'))
                    or event.get('origin') != list(origin)):
                issues.append(f'event {seq}: invalid grid path, origin or action cost')
                continue
            occupied = {point for name, point in positions.items() if name != actor}
            current = origin
            for point in path:
                point = tuple(point)
                distance = max(abs(point[0] - current[0]), abs(point[1] - current[1]))
                if distance != 1 or point in occupied:
                    issues.append(f'event {seq}: nonadjacent or occupied grid step')
                current = point
            if event.get('destination') != list(current):
                issues.append(f'event {seq}: grid destination mismatch')
            positions[actor] = current
        elif kind in ('group_hit_check', 'attack'):
            target = event.get('target')
            if actor not in positions or target not in positions or actor == target:
                issues.append(f'event {seq}: unknown grid attack participants')
                continue
            a, b = positions[actor], positions[target]
            dx, dy = b[0] - a[0], b[1] - a[1]
            distance = max(abs(dx), abs(dy))
            attack = attacks.get(event.get('trigger'))
            mode = attack.get('mode') if attack is not None else None
            if mode == 'ranged':
                reach = by_name[actor].ranged_range
                straight = dx == 0 or dy == 0 or abs(dx) == abs(dy)
                sx, sy = (dx > 0) - (dx < 0), (dy > 0) - (dy < 0)
                blocked = any((a[0] + sx * step, a[1] + sy * step) in positions.values()
                              for step in range(1, distance)) if straight else True
                if not reach or distance > 2 * reach or distance > 200 or not straight or blocked:
                    issues.append(f'event {seq}: ranged target outside grid scope or blocked sight')
                if (type(event.get('troubles')) is not int
                        or event['troubles'] != int(target in dodging) + int(distance > reach)):
                    issues.append(f'event {seq}: incorrect ranged trouble at grid distance')
            elif not isinstance(mode, str) or distance != 1:
                issues.append(f'event {seq}: close target outside grid reach')
            if kind == 'attack' and (type(event.get('distance')) is not int or event['distance'] != distance):
                issues.append(f'event {seq}: attack distance disagrees with grid positions')
        elif kind == 'movement':
            issues.append(f'event {seq}: legacy movement is not supported on this grid')
        elif kind == 'knockback':
            issues.append(f'event {seq}: grid knockback is outside the model')
    if tuple(positions[name] for name in names) != tuple(tuple(p) for p in final_positions):
        issues.append('final group grid positions mismatch')
    return issues
