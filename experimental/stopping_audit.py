"""Independent Stopping Power transaction audit layered over ParryDuel ledgers."""

from .parry_audit import audit_parry_duel


def audit_stopping_duel(result, profiles, *, ranged_weapons, **context):
    profiles = tuple(profiles)
    if len(profiles) != 2 or len({p.name for p in profiles}) != 2:
        raise ValueError('Exactly two distinct profiles are required')
    names = {p.name: p for p in profiles}
    if not isinstance(result.log, (list, tuple)) or any(not isinstance(e, dict) for e in result.log):
        return ['Invalid experimental event log']
    health = {p.name: p.max_health for p in profiles}
    focus = {p.name: p.max_focus for p in profiles}
    stunned = dict.fromkeys(names, False)
    active, distance, pending, next_id = None, context.get('initial_distance'), None, 1
    parry_pending, consider = False, []
    issues = []
    for index, event in enumerate(result.log):
        kind, actor, target, seq = event.get('type'), event.get('actor'), event.get('target'), event.get('seq')
        if ((actor is not None and not isinstance(actor, str))
                or (target is not None and not isinstance(target, str))):
            issues.append(f'event {seq}: invalid actor or target')
            continue
        if kind == 'turn_start':
            active = actor
        elif kind == 'turn_end':
            if pending is not None:
                issues.append(f'event {seq}: Stopping Power still open at end of turn')
            active = None
        elif kind in ('movement', 'knockback'):
            distance = event.get('distance_after')
        elif kind == 'condition_start' and actor in stunned and event.get('condition') == 'stunned':
            stunned[actor] = True
        elif kind == 'condition_end' and actor in stunned and event.get('condition') == 'stunned':
            stunned[actor] = False
        elif kind == 'parry_start':
            parry_pending = True
        elif kind == 'parry_end':
            parry_pending = False
        elif kind == 'reaction_queued' and actor in names and 'point_blank_parry' in names[actor].powers:
            consider.append((actor, event.get('source'), event.get('trigger')))
        elif kind == 'reaction_considered':
            key = (actor, event.get('source'), event.get('trigger'))
            if key in consider:
                consider.remove(key)
        if kind == 'stopping_start':
            p, use_id = names.get(actor), event.get('use_id')
            if (pending is not None or p is None or target not in names or target == actor
                    or actor != active or 'stopping_power' not in p.powers or 'double_tap' not in p.powers
                    or p.rank < 2 or p.ranged_range < 1 or type(distance) is not int
                    or not 1 <= distance <= 2 * p.ranged_range or event.get('distance') != distance
                    or type(focus.get(actor)) is not int or focus[actor] < 6
                    or type(health.get(actor)) is not int or health[actor] <= 0 or stunned.get(actor)
                    or type(health.get(target)) is not int or health[target] <= 0
                    or type(use_id) is not int or use_id != next_id):
                issues.append(f'event {seq}: invalid Stopping Power declaration')
            next_id += 1
            pending = {'actor': actor, 'target': target, 'id': use_id, 'cost': False,
                       'initial': None, 'decision': None, 'followup': None}
        elif kind == 'focus_spent' and actor in focus:
            if (type(event.get('amount')) is not int or type(event.get('focus_before')) is not int
                    or type(event.get('focus_after')) is not int or focus[actor] != event['focus_before']
                    or event['focus_before'] - event['amount'] != event['focus_after']):
                issues.append(f'event {seq}: Focus ledger mismatch')
            else:
                focus[actor] = event['focus_after']
            if event.get('source') == 'stopping_power':
                previous = result.log[index - 1] if index else {}
                if (pending is None or pending['cost'] or actor != pending['actor']
                        or event.get('stopping_use_id') != pending['id'] or event.get('amount') != 5
                        or type(event.get('focus_after')) is not int or event['focus_after'] < 1
                        or previous.get('type') != 'stopping_start'
                        or previous.get('actor') != actor or previous.get('use_id') != pending['id']):
                    issues.append(f'event {seq}: invalid Stopping Power Focus cost')
                if pending is not None:
                    pending['cost'] = True
        elif kind == 'attack' and actor in names and target in names:
            use_id, role = event.get('stopping_use_id'), event.get('stopping_role')
            if use_id is not None or role is not None:
                if (pending is None or actor != pending['actor'] or target != pending['target']
                        or use_id != pending['id'] or role not in ('initial', 'followup')
                        or event.get('reaction') is not False or event.get('mode') != 'ranged'
                        or not pending['cost']):
                    issues.append(f'event {seq}: invalid Stopping Power attack')
                elif role == 'initial':
                    if pending['initial'] is not None or pending['decision'] is not None:
                        issues.append(f'event {seq}: duplicate or late initial attack')
                    pending['initial'] = event
                else:
                    if (pending['initial'] is None or pending['decision'] is not True
                            or pending['followup'] is not None
                            or event.get('trigger') == pending['initial'].get('trigger')):
                        issues.append(f'event {seq}: invalid or duplicate follow-up attack')
                    pending['followup'] = event
            health[target] = event.get('health_after')
        elif kind == 'ram_attack' and actor in names and target in names:
            health[actor], health[target] = event.get('attacker_health_after'), event.get('target_health_after')
        elif kind in ('heal', 'condition_tick') and actor in names:
            health[actor] = event.get('health_after')
        elif kind == 'stopping_decision':
            initial = pending.get('initial') if pending is not None else None
            if initial is None or actor not in names or target not in names:
                issues.append(f'event {seq}: decision has no initial attack')
            else:
                eligible = (initial.get('success') is True and initial.get('fantastic') is True
                            and type(health[actor]) is int and health[actor] > 0 and not stunned[actor]
                            and type(health[target]) is int and health[target] > 0)
                if (actor != pending['actor'] or target != pending['target']
                        or event.get('use_id') != pending['id'] or event.get('trigger') != initial.get('trigger')
                        or type(event.get('eligible')) is not bool or event['eligible'] is not eligible
                        or type(event.get('used')) is not bool or event['used'] and not eligible
                        or pending['decision'] is not None or consider or parry_pending):
                    issues.append(f'event {seq}: invalid or premature follow-up decision')
                pending['decision'] = event.get('used')
        elif kind == 'stopping_end':
            if (pending is None or actor != pending['actor'] or target != pending['target']
                    or event.get('use_id') != pending['id'] or not pending['cost']
                    or pending['initial'] is None or type(pending['decision']) is not bool
                    or type(event.get('followed_up')) is not bool
                    or event['followed_up'] is not pending['decision']
                    or (pending['followup'] is not None) is not pending['decision']
                    or consider or parry_pending):
                issues.append(f'event {seq}: incomplete Stopping Power transaction')
            pending = None
    if pending is not None:
        issues.append('Unfinished Stopping Power transaction')
    if issues:
        return issues
    return audit_parry_duel(result, profiles, ranged_weapons=ranged_weapons,
                            allow_experimental_stopping=True, **context)
