"""Independent arithmetic and ledger checks for saved duel logs.

This intentionally does not import the damage or dice implementation.
"""

from __future__ import annotations

from math import ceil


def audit_log(log: tuple[dict, ...] | list[dict],
              initial_health: dict[str, int],
              initial_focus: dict[str, int]) -> list[str]:
    issues: list[str] = []
    health = dict(initial_health)
    focus = dict(initial_focus)
    standard_actions: dict[tuple[str, int, bool], int] = {}
    bonus_actions: dict[tuple[str, int, bool], int] = {}
    reaction_remaining: dict[str, int] = {}
    reaction_reset_seen: set[tuple[str, int, bool]] = set()
    reacted_triggers: set[tuple[str, int]] = set()
    last_seq = 0
    for index, event in enumerate(log):
        seq = event["seq"]
        if seq != last_seq + 1:
            issues.append(f"event {seq}: non-consecutive sequence")
        last_seq = seq
        kind = event["type"]
        actor = event.get("actor")
        turn_key = (actor, event["round"], event["bonus_round"])
        if kind == "reaction_reset":
            if turn_key in reaction_reset_seen:
                issues.append(f"event {seq}: duplicate reaction reset within round")
            reaction_reset_seen.add(turn_key)
            reaction_remaining[actor] = event["reactions"]
        if kind == "turn_start":
            if turn_key not in reaction_reset_seen:
                issues.append(f"event {seq}: missing reaction reset for round")
            previous = reaction_remaining.get(actor)
            if previous is not None and previous != event["reactions"]:
                issues.append(f"event {seq}: reaction budget changed within round")
            reaction_remaining[actor] = event["reactions"]
        if kind == "reaction_spent":
            remaining = event["remaining"]
            if remaining < 0:
                issues.append(f"event {seq}: negative reaction budget")
            previous = reaction_remaining.get(actor)
            if previous is not None and previous - 1 != remaining:
                issues.append(f"event {seq}: reaction ledger mismatch")
            reaction_remaining[actor] = remaining
            trigger = event.get("trigger")
            if trigger is not None:
                key = (actor, trigger)
                if key in reacted_triggers:
                    issues.append(f"event {seq}: duplicate reaction to one trigger")
                reacted_triggers.add(key)
        if kind == "attack":
            left, marvel, right = event["roll"]
            if not all(1 <= x <= 6 for x in (left, marvel, right)):
                issues.append(f"event {seq}: invalid die face")
            die_value = 6 if marvel == 1 else marvel
            total = left + die_value + right + event["check_modifier"]
            ultimate = (left, marvel, right) == (6, 1, 6)
            fantastic = marvel == 1
            success = ultimate or total >= event["target_number"]
            if (total != event["total"] or ultimate != event["ultimate"]
                    or fantastic != event["fantastic"] or success != event["success"]):
                issues.append(f"event {seq}: check classification mismatch")
            calculated = 0
            if success and not event["ammunition_immunity"]:
                multiplier = (event["rank"] + max(0, *event["bonus_candidates"])
                              - event["reduction"])
                if multiplier >= 1:
                    regular = max(0, die_value * multiplier
                                  + event["ability_for_damage"])
                    fantastic_factor = (2 if fantastic and
                                        event["default_fantastic_multiplier"] else 1)
                    calculated = ceil(regular * fantastic_factor /
                                      event["damage_denominator"])
            if calculated != event["calculated_damage"]:
                issues.append(f"event {seq}: damage arithmetic mismatch")
            before, after = event["health_before"], event["health_after"]
            if health.get(event["target"]) != before:
                issues.append(f"event {seq}: target Health ledger mismatch")
            if before - after != event["damage"]:
                issues.append(f"event {seq}: applied damage ledger mismatch")
            if not 0 <= event["damage"] <= calculated:
                issues.append(f"event {seq}: applied damage outside allowed range")
            health[event["target"]] = after
            if not event["reaction"]:
                standard_actions[turn_key] = standard_actions.get(turn_key, 0) + 1
        elif kind == "movement" and event["as_standard"]:
            standard_actions[turn_key] = standard_actions.get(turn_key, 0) + 1
        elif kind in ("stance", "dodge", "focus_spent", "wait",
                      "condition_treatment"):
            standard_actions[turn_key] = standard_actions.get(turn_key, 0) + 1
        elif kind == "shield_activate" and event["cost"] == "standard":
            standard_actions[turn_key] = standard_actions.get(turn_key, 0) + 1
        if kind == "shield_activate" and event["cost"] == "reaction":
            if (index == 0 or log[index - 1]["type"] != "reaction_spent"
                    or log[index - 1]["actor"] != actor):
                issues.append(f"event {seq}: shield reaction has no cost event")
        if kind == "condition_treatment":
            left, marvel, right = event["roll"]
            total = left + (6 if marvel == 1 else marvel) + right + event["check_modifier"]
            ultimate = (left, marvel, right) == (6, 1, 6)
            if (total != event["total"] or (ultimate or total >= event["target_number"]) != event["success"]
                    or ultimate != event["ultimate"] or (marvel == 1) != event["fantastic"]):
                issues.append(f"event {seq}: treatment check mismatch")
            if event["success"] and event["remaining_intensity"] != 0:
                issues.append(f"event {seq}: successful treatment left bleeding")
        if kind == "blade_bonus":
            bonus_actions[turn_key] = bonus_actions.get(turn_key, 0) + 1
        if kind in ("heal", "condition_tick"):
            before, after = event["health_before"], event["health_after"]
            if health.get(actor) != before:
                issues.append(f"event {seq}: Health ledger mismatch")
            if kind == "heal" and after - before != event["effective"]:
                issues.append(f"event {seq}: effective healing mismatch")
            if kind == "condition_tick" and before - after != event["damage"]:
                issues.append(f"event {seq}: condition damage mismatch")
            health[actor] = after
        if kind == "focus_spent":
            if focus.get(actor) != event["focus_before"]:
                issues.append(f"event {seq}: Focus ledger mismatch")
            if event["focus_before"] - event["focus_after"] != event["amount"]:
                issues.append(f"event {seq}: Focus cost mismatch")
            focus[actor] = event["focus_after"]
        if kind == "turn_end":
            if health.get(actor) != event["health"] or focus.get(actor) != event["focus"]:
                issues.append(f"event {seq}: end-of-turn state mismatch")
    for key, count in standard_actions.items():
        allowed = 1 + int(bonus_actions.get(key, 0) > 0)
        if count > allowed:
            issues.append(f"{key}: too many standard attacks/actions: {count}")
    for key, count in bonus_actions.items():
        if count > 1:
            issues.append(f"{key}: more than one blade bonus")
    return issues
