"""Independent arithmetic and resource ledger for FocusDuel full logs.

This module does not import the production dice or damage functions.
"""


def audit_focus_duel(result: object, profiles: tuple[object, object],
                     shield_focus_reduction: int) -> list[str]:
    issues: list[str] = []
    by_name = {p.name: p for p in profiles}
    health = {p.name: p.max_health for p in profiles}
    focus = {p.name: p.max_focus for p in profiles}
    shield = {p.name: p.shield_active for p in profiles}
    reactions: dict[str, int] = {}
    reacted: set[tuple[str, int]] = set()
    resets: set[tuple[str, int, bool]] = set()
    actions: dict[tuple[str, int, bool], int] = {}
    checks: dict[int, dict] = {}
    targets_seen: set[int] = set()
    demoralized_ever = False
    prior = 0
    for event in result.log:
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
        elif kind == "reaction_spent":
            if reactions.get(actor, 0) - 1 != event["remaining"]:
                issues.append(f"event {seq}: reaction budget mismatch")
            reactions[actor] = event["remaining"]
            if event.get("trigger") is not None:
                pair = (actor, event["trigger"])
                if pair in reacted:
                    issues.append(f"event {seq}: two reactions on one trigger")
                reacted.add(pair)
        elif kind == "shield_activate":
            if shield[actor] or "shield" not in by_name[actor].weapons:
                issues.append(f"event {seq}: illegal shield activation")
            shield[actor] = True
        elif kind == "shield_deactivate":
            if not shield[actor]:
                issues.append(f"event {seq}: shield deactivated while inactive")
            shield[actor] = False
        elif kind == "turn_start":
            if key not in resets or reactions.get(actor) != event["reactions"]:
                issues.append(f"event {seq}: turn reaction mismatch")
            if focus[actor] != event["focus"]:
                issues.append(f"event {seq}: turn Focus mismatch")
        elif kind == "attack_check":
            trigger = event["trigger"]
            if trigger in checks:
                issues.append(f"event {seq}: duplicate attack trigger")
            checks[trigger] = event
            roll = event["roll"]
            if len(roll) != 3 or any(not 1 <= face <= 6 for face in roll):
                issues.append(f"event {seq}: invalid roll")
                continue
            marvel = 6 if roll[1] == 1 else roll[1]
            total = sum((roll[0], marvel, roll[2], event["modifier"]))
            success = total >= event["defense"] or roll == [6, 1, 6]
            if (total != event["total"] or success != event["success"]
                    or (roll[1] == 1) != event["fantastic"]):
                issues.append(f"event {seq}: attack classification mismatch")
            expected_edges = int("blazing_fast_fists" in by_name[actor].powers)
            if (event["edges"] != expected_edges or
                    event["troubles"] != int(focus[actor] <= 0)):
                issues.append(f"event {seq}: edge or demoralized trouble mismatch")
            if not event["reaction"]:
                actions[key] = actions.get(key, 0) + 1
        elif kind == "attack_target":
            trigger = event["trigger"]
            check = checks.get(trigger)
            if check is None or trigger in targets_seen:
                issues.append(f"event {seq}: target without unique attack check")
                continue
            targets_seen.add(trigger)
            if (check["target"] != event["target"] or
                    check["kind"] != event["kind"]):
                issues.append(f"event {seq}: attack target mismatch")
            attacker = by_name[actor]
            defender = by_name[event["target"]]
            faces = event["damage_faces"]
            if any(not 1 <= face <= 6 for face in faces):
                issues.append(f"event {seq}: invalid damage die face")
            def expected_pool(multiplier: int, reduction: int) -> int:
                count = max(0, multiplier - reduction) if check["success"] else 0
                if len(faces) != count:
                    issues.append(f"event {seq}: damage dice count mismatch")
                subtotal = (sum(6 if face == 1 else face for face in faces)
                            + attacker.melee) if count else 0
                return max(0, subtotal) * (2 if check["fantastic"] else 1)
            if event["kind"] == "hammer":
                bonus = (attacker.melee_bonus + 2 if "mighty" in attacker.powers
                         else max(attacker.melee_bonus, 2))
                reduction = defender.health_dr
                calculated = expected_pool(attacker.rank + bonus, reduction)
                before = health[defender.name]
                after = before - calculated
                if attacker.heroic and after <= -defender.max_health:
                    after = -defender.max_health + 1
                if (event["health_before"] != before or
                        event["health_after"] != after or
                        event["reduction"] != reduction):
                    issues.append(f"event {seq}: Health ledger mismatch")
                health[defender.name] = event["health_after"]
            elif event["kind"] == "mental_punch":
                reduction = shield_focus_reduction if shield[defender.name] else 0
                calculated = expected_pool(attacker.rank, reduction)
                before = focus[defender.name]
                after = before - calculated
                if attacker.heroic and after <= -defender.max_focus:
                    after = -defender.max_focus + 1
                if (event["focus_before"] != before or
                        event["focus_after"] != after or
                        event["reduction"] != reduction or
                        event["demoralized"] != (after <= 0) or
                        event["shattered"] != (after <= -defender.max_focus)):
                    issues.append(f"event {seq}: Focus ledger mismatch")
                focus[defender.name] = event["focus_after"]
                demoralized_ever |= after <= 0
            else:
                issues.append(f"event {seq}: unknown damage kind")
                continue
            if (event["calculated_damage"] != calculated or
                    event["applied"] != before - after):
                issues.append(f"event {seq}: damage arithmetic mismatch")
        elif kind == "heal":
            expected = min(by_name[actor].max_health,
                           health[actor] + by_name[actor].resilience)
            if (event["health_before"] != health[actor] or
                    event["health_after"] != expected):
                issues.append(f"event {seq}: healing ledger mismatch")
            health[actor] = event["health_after"]
        elif kind == "turn_end":
            if (event["health"] != health[actor] or
                    event["focus"] != focus[actor]):
                issues.append(f"event {seq}: end-turn resource mismatch")
    for key, count in actions.items():
        if count > 1:
            issues.append(f"{key}: multiple standard attacks")
    if set(checks) != targets_seen:
        issues.append("attack checks without targets")
    if tuple(health[p.name] for p in profiles) != result.final_health:
        issues.append("final Health mismatch")
    if tuple(focus[p.name] for p in profiles) != result.final_focus:
        issues.append("final Focus mismatch")
    if demoralized_ever != result.ever_demoralized:
        issues.append("ever-demoralized mismatch")
    expected_outcome = (
        "loss" if health[profiles[0].name] <= 0 or
        focus[profiles[0].name] <= -profiles[0].max_focus else
        "win" if health[profiles[1].name] <= 0 or
        focus[profiles[1].name] <= -profiles[1].max_focus else
        "inconclusive")
    if result.outcome != expected_outcome:
        issues.append("final outcome mismatch")
    return issues
