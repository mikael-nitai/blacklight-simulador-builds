"""Independent position ledger for the bounded one-cell-wide corridor."""


def audit_corridor(log: tuple[dict, ...] | list[dict],
                   names: tuple[str, str], *,
                   initial_positions: tuple[int, int], length: int,
                   final_positions: tuple[int, int],
                   wall_reached: bool | None = None,
                   contact_occurred: bool | None = None) -> list[str]:
    issues: list[str] = []
    positions = list(initial_positions)
    saw_wall = positions[1] == length
    saw_contact = positions[1] - positions[0] <= 1
    for event in log:
        seq = event["seq"]
        if event["type"] == "knockback":
            issues.append(f"event {seq}: unmodeled corridor knockback")
        if event["type"] == "movement":
            actor = names.index(event["actor"])
            before = tuple(positions)
            x = positions[actor]
            steps = event["steps"]
            if steps < 0:
                issues.append(f"event {seq}: negative movement")
                continue
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
            if event["distance"] != positions[1] - positions[0]:
                issues.append(f"event {seq}: attack distance mismatch")
    if tuple(positions) != final_positions:
        issues.append("final position mismatch")
    if wall_reached is not None and saw_wall != wall_reached:
        issues.append("wall-reaching flag mismatch")
    if contact_occurred is not None and saw_contact != contact_occurred:
        issues.append("contact flag mismatch")
    return issues
