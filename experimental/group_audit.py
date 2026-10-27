"""Independent d616/damage/action ledger for fixed-contact group logs.

This module does not import production dice or damage functions.
"""

from math import ceil


def audit_group_log(log: tuple[dict, ...] | list[dict],
                    profiles: tuple[object, ...]) -> list[str]:
    issues: list[str] = []
    by_name = {p.name: p for p in profiles}
    health = {p.name: p.max_health for p in profiles}
    focus = {p.name: p.max_focus for p in profiles}
    shield = {p.name: p.shield_active for p in profiles}
    reactions: dict[str, int] = {}
    resets: set[tuple[str, int, bool]] = set()
    actions: dict[tuple[str, int, bool], int] = {}
    checks: dict[int, dict] = {}
    targets_seen: set[tuple[int, str]] = set()
    reacted: set[tuple[str, int]] = set()
    prior = 0
    for index, event in enumerate(log):
        seq = event["seq"]
        if seq != prior + 1:
            issues.append(f"event {seq}: non-consecutive sequence")
        prior = seq
        kind = event["type"]
        actor = event.get("actor")
        key = (actor, event["round"], event["bonus_round"])
        if kind == "reaction_reset":
            if key in resets:
                issues.append(f"event {seq}: duplicate reaction reset")
            resets.add(key)
            expected = 1 + int("combat_reflexes" in by_name[actor].traits)
            if event["reactions"] != expected:
                issues.append(f"event {seq}: wrong reaction budget")
            reactions[actor] = event["reactions"]
        elif kind == "turn_start":
            if key not in resets:
                issues.append(f"event {seq}: missing reaction reset")
            if reactions.get(actor) != event["reactions"]:
                issues.append(f"event {seq}: reaction ledger mismatch at turn start")
        elif kind == "reaction_spent":
            amount = event["remaining"]
            if reactions.get(actor, 0) - 1 != amount or amount < 0:
                issues.append(f"event {seq}: reaction ledger mismatch")
            reactions[actor] = amount
            trigger = event.get("trigger")
            if trigger is not None:
                pair = (actor, trigger)
                if pair in reacted:
                    issues.append(f"event {seq}: two reactions on one trigger")
                reacted.add(pair)
        elif kind == "shield_activate" and event["cost"] == "reaction":
            if (index == 0 or log[index - 1]["type"] != "reaction_spent"
                    or log[index - 1]["actor"] != actor):
                issues.append(f"event {seq}: shield activation lacks reaction cost")
            if shield[actor] or "shield" not in by_name[actor].weapons:
                issues.append(f"event {seq}: illegal shield activation")
            shield[actor] = True
        elif kind == "shield_deactivate":
            if not shield[actor]:
                issues.append(f"event {seq}: shield deactivated while inactive")
            shield[actor] = False
        elif kind == "attack_check":
            trigger = event["trigger"]
            if trigger in checks:
                issues.append(f"event {seq}: duplicate attack check trigger")
            checks[trigger] = event
            roll = event["roll"]
            if len(roll) != 3 or not all(1 <= v <= 6 for v in roll):
                issues.append(f"event {seq}: invalid roll")
            else:
                total = roll[0] + (6 if roll[1] == 1 else roll[1]) + roll[2]
                total += event["check_modifier"]
                if total != event["total"]:
                    issues.append(f"event {seq}: wrong attack total")
            if event["mode"] == "fast_strikes":
                if not 1 <= len(event["targets"]) <= 2:
                    issues.append(f"event {seq}: fast target count")
            elif len(event["targets"]) != 1:
                issues.append(f"event {seq}: single attack target count")
            if len(set(event["targets"])) != len(event["targets"]):
                issues.append(f"event {seq}: duplicate target in attack")
            if not event["reaction"]:
                actions[key] = actions.get(key, 0) + 1
        elif kind == "wait":
            actions[key] = actions.get(key, 0) + 1
        elif kind == "attack_target":
            trigger = event["trigger"]
            check = checks.get(trigger)
            if check is None:
                issues.append(f"event {seq}: target without attack check")
                continue
            target = event["target"]
            if target not in check["targets"] or (trigger, target) in targets_seen:
                issues.append(f"event {seq}: missing or duplicate target")
            targets_seen.add((trigger, target))
            attacker = by_name[check["actor"]]
            defender = by_name[target]
            roll = check["roll"]
            marvel = 6 if roll[1] == 1 else roll[1]
            total = roll[0] + marvel + roll[2] + check["check_modifier"]
            fantastic = roll[1] == 1
            ultimate = roll == [6, 1, 6]
            success = ultimate or total >= event["defense"]
            if (success != event["success"] or fantastic != event["fantastic"]
                    or event["mode"] != check["mode"]):
                issues.append(f"event {seq}: target classification mismatch")
            bonus = attacker.melee_bonus
            if event["mode"] == "hammer":
                bonus = (bonus + 2 if "mighty" in attacker.powers
                         else max(bonus, 2))
            multiplier = attacker.rank + max(0, bonus) - event["reduction"]
            if not success or multiplier < 1:
                calculated = 0
            else:
                regular = max(0, marvel * multiplier + attacker.melee)
                if event["mode"] == "fast_strikes":
                    calculated = ceil(regular / (1 if fantastic else 2))
                else:
                    calculated = regular * (2 if fantastic else 1)
            if calculated != event["calculated_damage"]:
                issues.append(f"event {seq}: damage arithmetic mismatch")
            before, after = event["health_before"], event["health_after"]
            if before != health.get(target) or before - after != event["damage"]:
                issues.append(f"event {seq}: Health ledger mismatch")
            expected_reduction = defender.health_dr + (2 if shield[target] else 0)
            if event["reduction"] != expected_reduction:
                issues.append(f"event {seq}: damage reduction ledger mismatch")
            expected_after = before - calculated
            if attacker.heroic and expected_after <= -defender.max_health:
                expected_after = -defender.max_health + 1
            if after != expected_after:
                issues.append(f"event {seq}: applied damage mismatch")
            health[target] = after
        elif kind == "heal":
            before, after = event["health_before"], event["health_after"]
            if (before != health.get(actor) or after - before != event["effective"]
                    or after > by_name[actor].max_health):
                issues.append(f"event {seq}: healing ledger mismatch")
            health[actor] = after
        elif kind == "turn_end":
            if event["health"] != health.get(actor) or event["focus"] != focus.get(actor):
                issues.append(f"event {seq}: end-of-turn ledger mismatch")
    for key, count in actions.items():
        if count > 1:
            issues.append(f"{key}: more than one standard action")
    for trigger, check in checks.items():
        observed = {name for tid, name in targets_seen if tid == trigger}
        if observed != set(check["targets"]):
            issues.append(f"trigger {trigger}: attack targets not fully resolved")
    return issues


def audit_group_result(result: object, profiles: tuple[object, ...]) -> list[str]:
    """Audit a complete group battle including its terminal state."""
    issues = audit_group_log(result.log, profiles)
    final_health = tuple(_health_from_log(result.log, p) for p in profiles)
    if final_health != result.final_health:
        issues.append("final Health mismatch")
    if tuple(p.max_focus for p in profiles) != result.final_focus:
        issues.append("final Focus mismatch")
    expected = ("loss" if final_health[0] <= 0 else
                "win" if all(value <= 0 for value in final_health[1:]) else
                "inconclusive")
    if result.outcome != expected:
        issues.append("final outcome mismatch")
    return issues


def _health_from_log(log: tuple[dict, ...] | list[dict], profile: object) -> int:
    value = profile.max_health
    for event in log:
        if event["type"] == "attack_target" and event["target"] == profile.name:
            value = event["health_after"]
        elif event["type"] == "heal" and event["actor"] == profile.name:
            value = event["health_after"]
    return value
