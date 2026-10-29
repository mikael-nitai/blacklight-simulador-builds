"""Independent arithmetic and ledger checks for saved duel logs.

This intentionally does not import the damage or dice implementation.
"""

from __future__ import annotations

from math import ceil
from .dice_audit import audit_rerolls
from .profile_audit import audit_profile_facts
from .ruleset_audit import audit_ruleset_log
from .split_audit import audit_split_fast


def _audit_pool_attack(event: dict, seq: int) -> tuple[int, list[str]]:
    """Recompute literal Marvel pools without importing the engine's roller."""
    issues: list[str] = []
    fast = event["mode"] == "fast_strikes" or event["mode"].endswith("_fast")
    primary = (event["mode"][:-5] if event["mode"].endswith("_fast")
               else event["mode"])
    first = ("ranged" if primary == "ranged" else
             primary if primary in {"blade", "claw", "hammer"} else "bare")
    expected_weapons = ([first, event["offhand"] or first]
                        if fast and 'fast_use_id' not in event else [first])
    if event["strike_weapons"] != expected_weapons:
        issues.append(f"event {seq}: strike weapon ledger mismatch")
    components = event["damage_components"]
    if not event["success"]:
        if components:
            issues.append(f"event {seq}: damage components on miss")
        return 0, issues
    if len(components) != len(expected_weapons):
        issues.append(f"event {seq}: wrong number of damage components")
    total = 0
    for index, component in enumerate(components):
        if index >= len(expected_weapons):
            issues.append(f"event {seq}: surplus component {index}")
            continue
        if component["weapon"] != expected_weapons[index]:
            issues.append(f"event {seq}: component weapon mismatch")
        bonuses = component["bonus_candidates"]
        multiplier = event["rank"] + max(0, *bonuses)
        if multiplier != component["full_multiplier"]:
            issues.append(f"event {seq}: component multiplier mismatch")
        immunity = event["ammunition_immunity"]
        effective_dr = 0 if immunity else event["reduction"]
        after_dr = max(0, multiplier - effective_dr)
        if component["reduction"] != event["reduction"] or component[
                "dice_after_reduction"] != after_dr:
            issues.append(f"event {seq}: component reduction mismatch")
        count = (after_dr if event["fantastic"] or not fast
                 else after_dr // 2)
        ability = event["ability_for_damage"]
        if fast and not event["fantastic"]:
            if ability % 2:
                issues.append(f"event {seq}: unresolved odd ability half")
            ability //= 2
        bonus_survives = (after_dr > 0 and (count > 0 or event.get('fast_zero_dice_bonus', False)))
        if not bonus_survives:
            ability = 0
        faces = component["faces"]
        if (len(faces) != count or component["dice_rolled"] != count or
                component["ability_added"] != ability or
                any(not 1 <= face <= 6 for face in faces)):
            issues.append(f"event {seq}: component dice ledger mismatch")
        rolled = (max(0, sum(6 if face == 1 else face for face in faces)
                      + ability) if bonus_survives else 0)
        if event["fantastic"] and not fast:
            rolled *= 2
        applied = 0 if immunity else rolled
        if component["ammunition_immunity"] != immunity or component[
                "damage"] != applied:
            issues.append(f"event {seq}: component damage mismatch")
        total += applied
        raw_count = (multiplier if event["fantastic"] or not fast
                     else multiplier // 2)
        extra = component["counterfactual_faces"]
        if (len(extra) != (0 if immunity else max(0, raw_count - count)) or
                any(not 1 <= face <= 6 for face in extra)):
            issues.append(f"event {seq}: counterfactual dice ledger mismatch")
        raw_faces = faces if immunity else faces + extra
        raw_ability = (event["ability_for_damage"]
                       if event["fantastic"] or not fast else
                       event["ability_for_damage"] // 2)
        raw = (max(0, sum(6 if face == 1 else face for face in raw_faces)
                   + raw_ability) if multiplier > 0 and
               (raw_count > 0 or event.get('fast_zero_dice_bonus', False)) else 0)
        if event["fantastic"] and not fast:
            raw *= 2
        if component["damage_without_reduction"] != raw:
            issues.append(f"event {seq}: counterfactual damage mismatch")
    return total, issues


def audit_log(log: tuple[dict, ...] | list[dict],
              initial_health: dict[str, int],
              initial_focus: dict[str, int], *,
              reaction_limits: dict[str, int] | None = None,
              movement_limits: dict[str, int] | None = None,
              allow_experimental_parry: bool = False) -> list[str]:
    """Audit ledgers; supplied limits also check capabilities against profiles.

    Without the optional limits, a self-consistent ledger cannot establish how
    many reactions or movement spaces a combatant was actually entitled to.
    """
    if type(allow_experimental_parry) is not bool:
        raise ValueError('Experimental audit option must be boolean')
    for limits in (reaction_limits, movement_limits):
        if limits is not None and (not isinstance(limits, dict)
                                   or any(not isinstance(name, str) or type(value) is not int or value < 0
                                          for name, value in limits.items())):
            raise ValueError('Audit limits require names and nonnegative integer capacities')
    issues: list[str] = []
    health = dict(initial_health)
    focus = dict(initial_focus)
    standard_actions: dict[tuple[str, int, bool], int] = {}
    bonus_actions: dict[tuple[str, int, bool], int] = {}
    movement_actions: dict[tuple[str, int, bool], int] = {}
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
        if (kind in {'attack', 'movement', 'fast_use_start', 'stance', 'dodge',
                     'focus_spent', 'wait', 'condition_treatment', 'blade_bonus',
                     'reaction_spent', 'shield_activate'}
                and (actor not in health or health[actor] <= 0)):
            issues.append(f"event {seq}: unknown or unconscious actor performed an action")
        if kind == "reaction_reset":
            if turn_key in reaction_reset_seen:
                issues.append(f"event {seq}: duplicate reaction reset within round")
            reaction_reset_seen.add(turn_key)
            if (type(event.get('reactions')) is not int or event['reactions'] < 0
                    or reaction_limits is not None and
                    event['reactions'] != reaction_limits.get(actor)):
                issues.append(f"event {seq}: reaction budget exceeds or differs from the profile")
            if type(event.get('reactions')) is int and event['reactions'] >= 0:
                reaction_remaining[actor] = event['reactions']
            else:
                reaction_remaining.pop(actor, None)
        if kind == "turn_start":
            if turn_key not in reaction_reset_seen:
                issues.append(f"event {seq}: missing reaction reset for round")
            value = event.get('reactions')
            previous = reaction_remaining.get(actor)
            if type(value) is not int or value < 0:
                issues.append(f"event {seq}: invalid reaction budget at turn start")
                reaction_remaining.pop(actor, None)
            else:
                if previous is not None and previous != value:
                    issues.append(f"event {seq}: reaction budget changed within round")
                reaction_remaining[actor] = value
        if kind == "reaction_spent":
            remaining = event.get('remaining')
            if type(remaining) is not int or remaining < 0:
                issues.append(f"event {seq}: invalid reaction budget")
                reaction_remaining.pop(actor, None)
            else:
                previous = reaction_remaining.get(actor)
                restricted = (allow_experimental_parry and event.get('source') == 'point_blank_parry'
                              and event.get('pool') == 'fast_hands')
                if previous is not None and previous - (0 if restricted else 1) != remaining:
                    issues.append(f"event {seq}: reaction ledger mismatch")
                reaction_remaining[actor] = remaining
            trigger = event.get("trigger")
            if trigger is not None:
                key = (actor, trigger)
                if key in reacted_triggers:
                    issues.append(f"event {seq}: duplicate reaction to one trigger")
                reacted_triggers.add(key)
        if kind == 'fast_use_start':
            standard_actions[turn_key] = standard_actions.get(turn_key, 0) + 1
        if kind == "attack":
            if type(event.get('edges')) is not int or type(event.get('troubles')) is not int:
                issues.append(f"event {seq}: missing or invalid edge/trouble counts")
            else:
                issues.extend(audit_rerolls(event, edges=event['edges'], troubles=event['troubles']))
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
            if event.get("damage_model") == "literal_marvel_pool_v2":
                calculated, pool_issues = _audit_pool_attack(event, seq)
                issues.extend(pool_issues)
            elif success and not event["ammunition_immunity"]:
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
            if not event["reaction"] and 'fast_use_id' not in event:
                standard_actions[turn_key] = standard_actions.get(turn_key, 0) + 1
        elif kind == "movement":
            steps, direction, as_standard = (event.get('steps'), event.get('direction'),
                                             event.get('as_standard'))
            if (type(steps) is not int or steps < 0
                    or direction not in ('stay', 'approach', 'retreat')
                    or direction == 'stay' and steps != 0
                    or type(as_standard) is not bool
                    or movement_limits is not None and
                    (actor not in movement_limits or type(steps) is int
                     and steps > movement_limits[actor])):
                issues.append(f"event {seq}: invalid movement request or speed")
            if as_standard is True:
                standard_actions[turn_key] = standard_actions.get(turn_key, 0) + 1
            elif as_standard is False:
                movement_actions[turn_key] = movement_actions.get(turn_key, 0) + 1
        elif kind in ("stance", "dodge", "focus_spent", "wait",
                      "condition_treatment"):
            reactive_cost = (allow_experimental_parry and kind == 'focus_spent'
                             and event.get('reaction') is True and event.get('source') == 'point_blank_parry')
            if not reactive_cost:
                standard_actions[turn_key] = standard_actions.get(turn_key, 0) + 1
        elif kind == "shield_activate" and event["cost"] == "standard":
            standard_actions[turn_key] = standard_actions.get(turn_key, 0) + 1
        if kind == "shield_activate" and event["cost"] == "reaction":
            if (index == 0 or log[index - 1]["type"] != "reaction_spent"
                    or log[index - 1]["actor"] != actor):
                issues.append(f"event {seq}: shield reaction has no cost event")
        if kind == "condition_treatment":
            issues.extend(audit_rerolls(event, edges=0, troubles=0))
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
    for key, count in movement_actions.items():
        if count > 1:
            issues.append(f"{key}: more than one movement action")
    issues.extend(audit_split_fast(log))
    return issues


def audit_profiled_log(log: tuple[dict, ...] | list[dict], profiles, *, ruleset=None,
                       allow_experimental_parry=False) -> list[str]:
    """Audit a physical trace against profiles and, if supplied, its ruleset."""
    profiles = tuple(profiles)
    names = [profile.name for profile in profiles]
    if len(set(names)) != len(names):
        raise ValueError('Audit requires distinct combatant names')
    issues = audit_log(
        log,
        {p.name: p.max_health for p in profiles},
        {p.name: p.max_focus for p in profiles},
        reaction_limits={p.name: 2 if 'combat_reflexes' in p.traits else 1 for p in profiles},
        movement_limits={p.name: p.run_speed for p in profiles},
        allow_experimental_parry=allow_experimental_parry,
    )
    issues.extend(audit_profile_facts(log, profiles, allow_experimental_parry=allow_experimental_parry))
    if ruleset is not None:
        issues.extend(audit_ruleset_log(log, ruleset))
    return issues
