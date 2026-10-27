"""Independent position ledger for the bounded one-cell-wide corridor."""


def audit_corridor(log: tuple[dict, ...] | list[dict],
                   names: tuple[str, str], *,
                   initial_positions: tuple[int, int], length: int,
                   final_positions: tuple[int, int],
                   wall_reached: bool | None = None,
                   contact_occurred: bool | None = None) -> list[str]:
    issues: list[str] = []
    if (type(length) is not int or length < 1 or len(initial_positions) != 2
            or len(final_positions) != 2
            or any(type(value) is not int for value in (*initial_positions, *final_positions))
            or not 0 <= initial_positions[0] < initial_positions[1] <= length):
        return ['invalid integer corridor audit inputs']
    positions = list(initial_positions)
    saw_wall = positions[1] == length
    saw_contact = positions[1] - positions[0] <= 1
    for event in log:
        seq = event["seq"]
        if event["type"] == "knockback":
            issues.append(f"event {seq}: unmodeled corridor knockback")
        if event["type"] == "movement":
            if event['actor'] not in names:
                issues.append(f'event {seq}: unknown movement actor')
                continue
            actor = names.index(event["actor"])
            before = tuple(positions)
            x = positions[actor]
            steps = event["steps"]
            if type(steps) is not int or steps < 0:
                issues.append(f"event {seq}: movement requires nonnegative integer steps")
                continue
            if (any(type(event.get(key)) is not int for key in
                    ('actual_steps', 'distance_before', 'distance_after', 'corridor_length'))
                    or any(not isinstance(event.get(key), list) or len(event[key]) != 2
                           or any(type(value) is not int for value in event[key])
                           for key in ('positions_before', 'positions_after'))):
                issues.append(f'event {seq}: noninteger position ledger')
            if event["direction"] == "approach":
                positions[actor] = (
                    min(x + steps, positions[1] - 1) if actor == 0
                    else max(x - steps, positions[0] + 1))
            elif event["direction"] == "retreat":
                positions[actor] = (max(0, x - steps) if actor == 0
                                    else min(length, x + steps))
            elif event["direction"] != "stay" or steps != 0:
                issues.append(f"event {seq}: invalid direction or stay steps")
            if (event["positions_before"] != list(before) or
                    event["positions_after"] != positions or
                    event["distance_before"] != before[1] - before[0] or
                    event["distance_after"] != positions[1] - positions[0] or
                    event["actual_steps"] != abs(positions[actor] - x) or
                    event["corridor_length"] != length):
                issues.append(f"event {seq}: position ledger mismatch")
            if not 0 <= positions[0] < positions[1] <= length:
                issues.append(f"event {seq}: crossed wall or character")
            saw_wall |= positions[1] == length
            saw_contact |= positions[1] - positions[0] <= 1
        elif event["type"] == "attack":
            if type(event['distance']) is not int or event["distance"] != positions[1] - positions[0]:
                issues.append(f"event {seq}: attack distance mismatch")
    if tuple(positions) != final_positions:
        issues.append("final position mismatch")
    if wall_reached is not None and saw_wall != wall_reached:
        issues.append("wall-reaching flag mismatch")
    if contact_occurred is not None and saw_contact != contact_occurred:
        issues.append("contact flag mismatch")
    return issues
