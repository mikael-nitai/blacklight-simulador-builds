"""Independent Fast Hands / Point-Blank Parry ledger and full-duel audit."""

from .smg_audit import audit_submachine_duel


def audit_parry_duel(result, profiles, *, ranged_weapons, nested_reactions_first=False, **context):
    profiles = tuple(profiles)
    if (len(profiles) != 2 or len({p.name for p in profiles}) != 2
            or type(nested_reactions_first) is not bool):
        raise ValueError('Exactly two distinct profiles are required')
    if any('point_blank_parry' in p.powers and (p.rank < 2 or p.ranged_range < 1)
           or 'fast_hands' in p.powers and (p.rank < 3 or 'point_blank_parry' not in p.powers)
           for p in profiles):
        raise ValueError('Invalid Point-Blank Parry or Fast Hands prerequisites')
    names = {p.name: p for p in profiles}
    if not isinstance(result.log, (list, tuple)) or any(not isinstance(event, dict) for event in result.log):
        return ['Invalid experimental event log']
    health = {p.name: p.max_health for p in profiles}
    focus = {p.name: p.max_focus for p in profiles}
    ordinary = dict.fromkeys(names, None)
    fast = dict.fromkeys(names, 0)
    stunned = dict.fromkeys(names, False)
    spent = {p.name: set() for p in profiles}
    reset_expected, reset_seen = set(), set()
    failed, failed_reactions, queued, pending_consideration = {}, {}, set(), []
    issues, pending, open_fast = [], None, None
    distance = context.get('initial_distance')
    log = result.log
    for index, event in enumerate(log):
        kind, actor, target, seq = event.get('type'), event.get('actor'), event.get('target'), event.get('seq')
        if ((actor is not None and not isinstance(actor, str))
                or (target is not None and not isinstance(target, str))
                or type(event.get('round')) is not int or type(event.get('bonus_round')) is not bool):
            issues.append(f'event {seq}: invalid actor, target, or phase')
            continue
        if (kind in ('attack', 'ram_attack', 'reaction_queued', 'reaction_considered')
                and (type(event.get('trigger')) is not int or event['trigger'] < 1)
                or kind == 'reaction_spent' and event.get('trigger') is not None
                and (type(event['trigger']) is not int or event['trigger'] < 1)):
            issues.append(f'event {seq}: invalid reaction trigger')
            continue
        phase = (event.get('round'), event.get('bonus_round'), actor)
        if kind == 'reaction_reset' and actor in names:
            ordinary[actor] = event.get('reactions')
            fast[actor] = 0
            spent[actor].clear()
            if 'fast_hands' in names[actor].powers:
                reset_expected.add(phase)
        elif kind == 'fast_hands_reset':
            previous = log[index - 1] if index else {}
            if (actor not in names or phase not in reset_expected or phase in reset_seen
                    or 'fast_hands' not in names[actor].powers or type(event.get('reactions')) is not int
                    or event['reactions'] != 1
                    or previous.get('type') not in ('reaction_reset', 'fast_hands_reset')
                    or (previous.get('round'), previous.get('bonus_round')) != phase[:2]):
                issues.append(f'event {seq}: invalid Fast Hands reset')
            else:
                fast[actor] = 1
                reset_seen.add(phase)
        elif kind == 'movement':
            distance = event.get('distance_after')
        elif kind == 'knockback':
            distance = event.get('distance_after')
        elif kind == 'fast_use_start':
            open_fast = event.get('fast_use_id')
        elif kind == 'fast_use_end':
            open_fast = None
        elif kind == 'condition_start' and actor in stunned and event.get('condition') == 'stunned':
            stunned[actor] = True
        elif kind == 'condition_end' and actor in stunned and event.get('condition') == 'stunned':
            stunned[actor] = False

        if kind == 'attack' and actor in names and target in names:
            trigger = event.get('trigger')
            if event.get('success') is False:
                failed[trigger] = (actor, target, event.get('mode'))
                failed_reactions[trigger] = event.get('reaction') is True
            if event.get('reaction_power') == 'point_blank_parry':
                if (pending is None or pending.get('attack') is not None
                        or (actor, target, event.get('source_trigger')) !=
                           (pending['actor'], pending['target'], pending['source_trigger'])
                        or event.get('mode') != 'ranged' or event.get('reaction') is not True):
                    issues.append(f'event {seq}: parry attack does not match its declaration')
                elif pending is not None:
                    pending['attack'] = event
            health[target] = event.get('health_after')
        elif kind == 'ram_attack' and actor in names and target in names:
            health[actor], health[target] = event.get('attacker_health_after'), event.get('target_health_after')
            transaction = event.get('transaction')
            params = transaction.get('parameters') if isinstance(transaction, dict) else None
            if isinstance(params, dict) and params.get('success') is False:
                failed[event.get('trigger')] = (actor, target, 'melee')
        elif kind in ('heal', 'condition_tick') and actor in names:
            health[actor] = event.get('health_after')

        if kind == 'reaction_queued':
            trigger = event.get('trigger')
            if (trigger not in failed or failed[trigger][:2] != (event.get('source'), actor)
                    or trigger in queued):
                issues.append(f'event {seq}: reaction queue has no matching miss')
            else:
                queued.add(trigger)
                if actor in names and 'point_blank_parry' in names[actor].powers:
                    item = (actor, event.get('source'), trigger)
                    if nested_reactions_first and failed_reactions.get(trigger, False):
                        pending_consideration.insert(0, item)
                    else:
                        pending_consideration.append(item)
        elif kind == 'reaction_considered':
            expected = pending_consideration.pop(0) if pending_consideration else None
            if (expected is None or (actor, event.get('source'), event.get('trigger')) != expected
                    or open_fast is not None):
                issues.append(f'event {seq}: invalid or out-of-order reaction consideration')
        elif kind == 'reaction_spent' and actor in names:
            trigger = event.get('trigger')
            if trigger is not None:
                if trigger in spent[actor]:
                    issues.append(f'event {seq}: repeated reaction on same trigger')
                spent[actor].add(trigger)
            is_parry = event.get('source') == 'point_blank_parry'
            if 'POW-06' in event.get('rules', ()):
                source_miss = failed.get(trigger)
                if (trigger not in queued or source_miss is None or source_miss[1] != actor
                        or source_miss[2] == 'ranged' or type(distance) is not int or distance > 1):
                    issues.append(f'event {seq}: Riposte has no failed close attack')
            pool = event.get('pool') if is_parry else 'ordinary'
            if pool == 'ordinary':
                if type(ordinary[actor]) is not int or ordinary[actor] < 1:
                    issues.append(f'event {seq}: ordinary reaction unavailable')
                else:
                    ordinary[actor] -= 1
            elif pool == 'fast_hands':
                if not is_parry or fast[actor] != 1 or 'fast_hands' not in names[actor].powers:
                    issues.append(f'event {seq}: restricted reaction unavailable')
                else:
                    fast[actor] = 0
            else:
                issues.append(f'event {seq}: unknown reaction pool')
            if event.get('remaining') != ordinary[actor]:
                issues.append(f'event {seq}: ordinary reaction balance mismatch')
            if is_parry:
                prior = log[index - 1] if index else {}
                source = failed.get(trigger, (None, None, None))[0]
                if (pending is not None or trigger not in queued or source not in names
                        or prior.get('type') != 'reaction_considered' or prior.get('actor') != actor
                        or prior.get('source') != source or prior.get('trigger') != trigger
                        or 'point_blank_parry' not in names[actor].powers or names[actor].rank < 2
                        or names[actor].ranged_range < 1 or type(distance) is not int or not 1 <= distance <= 2
                        or type(focus[actor]) is not int or focus[actor] < 6
                        or type(health[actor]) is not int or health[actor] <= 0 or stunned[actor]
                        or type(health.get(source)) is not int or health[source] <= 0
                        or event.get('fast_hands_remaining') != fast[actor] or open_fast is not None):
                    issues.append(f'event {seq}: invalid Point-Blank Parry reaction')
                following = log[index + 1] if index + 1 < len(log) else {}
                if (following.get('type') != 'focus_spent' or following.get('actor') != actor
                        or following.get('source') != 'point_blank_parry'
                        or following.get('trigger') != trigger):
                    issues.append(f'event {seq}: parry reaction has no immediate Focus cost')
                pending = {'actor': actor, 'target': source, 'source_trigger': trigger,
                           'pool': pool, 'attack': None, 'condition': None, 'started': False}
        elif kind == 'focus_spent' and actor in names:
            if (type(event.get('amount')) is not int or type(event.get('focus_before')) is not int
                    or type(event.get('focus_after')) is not int or focus[actor] != event['focus_before']
                    or event['focus_before'] - event['amount'] != event['focus_after']):
                issues.append(f'event {seq}: Focus ledger mismatch')
            else:
                focus[actor] = event['focus_after']
            if event.get('source') == 'point_blank_parry':
                previous = log[index - 1] if index else {}
                if (pending is None or pending['actor'] != actor or event.get('amount') != 5
                        or event.get('reaction') is not True or type(event.get('focus_after')) is not int
                        or event['focus_after'] < 1
                        or previous.get('source') != 'point_blank_parry'
                        or previous.get('trigger') != event.get('trigger')):
                    issues.append(f'event {seq}: invalid parry Focus cost')
        elif kind == 'parry_start':
            previous = log[index - 1] if index else {}
            if (pending is None or pending['started'] or actor != pending['actor']
                    or target != pending['target'] or event.get('source_trigger') != pending['source_trigger']
                    or event.get('pool') != pending['pool'] or previous.get('type') != 'focus_spent'
                    or previous.get('source') != 'point_blank_parry'):
                issues.append(f'event {seq}: invalid parry declaration')
            if pending is not None:
                pending['started'] = True
        elif kind == 'condition_start' and 'CORE-P112-PARRY' in event.get('rules', ()):
            attack = pending.get('attack') if pending is not None else None
            if (attack is None or pending['condition'] is not None or actor != pending['target']
                    or event.get('condition') != 'bleeding' or type(event.get('intensity')) is not int
                    or event['intensity'] != 5 or event.get('trigger') != attack.get('trigger')):
                issues.append(f'event {seq}: invalid parry bleeding')
            if pending is not None:
                pending['condition'] = event
        elif kind == 'parry_end':
            attack = pending.get('attack') if pending is not None else None
            if attack is None or not pending['started']:
                issues.append(f'event {seq}: parry has no matching attack')
            else:
                bleeding = (attack.get('success') is True and attack.get('fantastic') is True
                            and attack.get('ammunition_immunity') is False)
                if (actor != pending['actor'] or target != pending['target']
                        or event.get('source_trigger') != pending['source_trigger']
                        or event.get('trigger') != attack.get('trigger')
                        or type(event.get('bleeding')) is not bool or event['bleeding'] is not bleeding
                        or (pending['condition'] is not None) is not bleeding):
                    issues.append(f'event {seq}: parry outcome or bleeding mismatch')
            pending = None
    if pending is not None:
        issues.append('Unfinished Point-Blank Parry')
    if pending_consideration:
        issues.append('Missed attack has an unprocessed reaction opportunity')
    if reset_expected != reset_seen:
        issues.append('Missing Fast Hands reset')
    if issues:
        return issues
    return audit_submachine_duel(result, profiles, ranged_weapons=ranged_weapons,
                                allow_experimental_parry=True, **context)
