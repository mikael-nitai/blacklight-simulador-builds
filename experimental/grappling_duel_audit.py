"""Validate grapple/escape chronology, then delegate the physical duel ledgers."""

from dataclasses import replace

from blacklight.dice import DieRoll, RerollTrace
from .adaptive_armed_melee_audit import audit_declared_armed_melee
from .grappling import EscapeResult, GrapplingResult, GrapplingState
from .grappling_audit import audit_escape, audit_grappling
from .reaction_pools import ReactionPools


def _state(data):
    data = dict(data)
    pools = dict(data['target_reactions'])
    pools['spent_triggers'] = frozenset(pools['spent_triggers'])
    data['target_reactions'] = ReactionPools(**pools)
    return GrapplingState(**data)


def _grapple(data):
    return GrapplingResult(_state(data['before']), _state(data['after']), data['attack_success'],
                           data['fantastic_success'], data['applied_damage'], data['trigger'])


def _escape(data):
    return EscapeResult(_state(data['before']), _state(data['after']), data['timing'], data['modifier'],
        data['target_number'], data['troubles'], DieRoll(**data['roll']),
        tuple(RerollTrace(**r) for r in data['rerolls']), data['total'], data['success'], data['trigger'])


def audit_grappling_duel(result, profiles, *, declared_armed_lethal, escape_trigger_mode, **context):
    profiles = tuple(profiles)
    names = {p.name: p for p in profiles}
    if (len(profiles) != 2 or len(names) != 2 or escape_trigger_mode not in ('attack', 'condition')):
        raise ValueError('Invalid grappling duel audit context')
    health = {p.name: p.max_health for p in profiles}
    focus = {p.name: p.max_focus for p in profiles}
    stunned = dict.fromkeys(names, False)
    reactions = dict.fromkeys(names, 0)
    fast = dict.fromkeys(names, 0)
    spent = {name: set() for name in names}
    holder, victim, pinned, active, pending, pending_reaction = None, None, False, None, None, None
    escape_opportunity = None
    projection, issues = [], []
    for index, event in enumerate(result.log):
        kind, actor, target, seq = (event.get('type'), event.get('actor'),
                                     event.get('target'), event.get('seq'))
        if type(seq) is not int or seq != index + 1:
            issues.append(f'event {seq}: invalid original sequence')
        if pending is not None and kind not in ('focus_spent', 'lethality_declaration',
                'prone_check', 'shield_deactivate', 'reaction_spent', 'shield_activate',
                'attack', 'reaction_queued', 'knockback_declined', 'grapple_end'):
            issues.append(f'event {seq}: unrelated event interrupted grapple action')
        if pending_reaction is not None and kind != 'grapple_escape':
            issues.append(f'event {seq}: escape reaction cost is not immediately resolved')
        if kind == 'turn_start':
            active = actor
        elif kind == 'turn_end':
            active = None
        elif kind == 'reaction_reset' and actor in names:
            reactions[actor], spent[actor] = event.get('reactions'), set()
        elif kind == 'fast_hands_reset' and actor in names:
            fast[actor] = event.get('reactions')
        elif kind == 'reaction_spent' and actor in names:
            trigger = event.get('trigger')
            old = (reactions[actor], fast[actor], frozenset(spent[actor]))
            if type(trigger) is int:
                spent[actor].add(trigger)
            if event.get('pool') == 'fast_hands':
                fast[actor] = 0
            else:
                reactions[actor] = event.get('remaining')
            if event.get('source') == 'grapple_escape':
                if (escape_opportunity is None or (actor, trigger) != escape_opportunity
                        or index == 0 or result.log[index - 1].get('type') != 'grapple_end'):
                    issues.append(f'event {seq}: escape reaction lacks the declared grapple trigger')
                pending_reaction = (actor, trigger, old)
        elif kind == 'condition_start' and event.get('condition') == 'stunned' and actor in stunned:
            stunned[actor] = True
        elif kind == 'condition_end' and event.get('condition') == 'stunned' and actor in stunned:
            stunned[actor] = False
        if kind == 'grapple_start':
            if (pending is not None or holder is not None or actor != active or actor not in names
                    or target not in names or actor == target or 'grappling_technique' not in names[actor].powers
                    or names[actor].rank < 2 or 'mighty' in names[actor].powers):
                issues.append(f'event {seq}: illegal grapple start')
            pending = {'actor': actor, 'target': target, 'focus': focus.get(actor), 'cost': False, 'attack': None}
            continue
        if kind == 'focus_spent' and actor in focus:
            if event.get('source') == 'grappling_technique':
                if (pending is None or actor != pending['actor'] or pending['cost'] or event.get('amount') != 5
                        or type(focus[actor]) is not int or focus[actor] < 6
                        or event.get('focus_before') != focus[actor] or event.get('focus_after') != focus[actor] - 5):
                    issues.append(f'event {seq}: invalid grapple Focus cost')
                if pending is not None:
                    pending['cost'] = True
            focus[actor] = event.get('focus_after')
        elif kind == 'attack':
            if holder is not None:
                issues.append(f'event {seq}: attack during unsupported hold')
            if pending is not None:
                if (pending['attack'] is not None or actor != pending['actor'] or target != pending['target']
                        or event.get('mode') != 'melee' or not pending['cost']):
                    issues.append(f'event {seq}: invalid grapple attack')
                pending['attack'] = event
            if target in health:
                health[target] = event.get('health_after')
        elif kind in ('heal', 'condition_tick') and actor in health:
            health[actor] = event.get('health_after')
        elif kind == 'ram_attack':
            if actor in health:
                health[actor] = event.get('attacker_health_after')
            if target in health:
                health[target] = event.get('target_health_after')
        elif kind == 'movement' and holder is not None:
            issues.append(f'event {seq}: movement during unsupported hold')
        if kind == 'grapple_end':
            try:
                attack = pending['attack']
                p, q = names[pending['actor']], names[pending['target']]
                tx = _grapple(event['transaction'])
                b = tx.before
                if (actor != pending['actor'] or target != pending['target'] or not pending['cost']
                        or attack is None or event.get('trigger') != attack.get('trigger')
                        or b.attacker_rank != p.rank or b.attacker_focus != pending['focus']
                        or b.attacker_standard is not True or b.attacker_conscious is not (health[p.name] > 0)
                        or b.attacker_stunned is not stunned[p.name] or b.target_health != attack['health_before']
                        or b.target_standard is not False or b.target_stunned is not stunned[q.name]
                        or b.target_reactions != ReactionPools(reactions[q.name], fast[q.name], frozenset(spent[q.name]))
                        or b.distance != 1 or b.grabbed or b.pinned):
                    issues.append(f'event {seq}: grapple state does not match combat')
                issues.extend(audit_grappling(tx, has_power='grappling_technique' in p.powers,
                    attack_success=attack['success'], fantastic_success=attack['success'] and attack['fantastic'],
                    applied_damage=attack['damage'], trigger=attack['trigger']))
                if attack['success']:
                    holder, victim, pinned = p.name, q.name, attack['fantastic']
                    escape_opportunity = (victim, attack['trigger'] + int(escape_trigger_mode == 'condition'))
                else:
                    escape_opportunity = None
            except (KeyError, TypeError, ValueError, AttributeError) as error:
                issues.append(f'event {seq}: malformed grapple transaction: {error}')
            pending = None
            continue
        if kind == 'grapple_escape':
            try:
                tx = _escape(event['transaction'])
                p, q = names[holder], names[victim]
                timing, trigger = event['timing'], event['trigger']
                old = (reactions[q.name], fast[q.name], frozenset(spent[q.name]))
                if timing == 'reaction':
                    if pending_reaction is None or pending_reaction[:2] != (victim, trigger):
                        issues.append(f'event {seq}: missing escape reaction cost')
                    else:
                        old = pending_reaction[2]
                elif timing != 'standard' or active != victim or pending_reaction is not None:
                    issues.append(f'event {seq}: invalid standard escape')
                b = tx.before
                if (actor != victim or target != holder or b.target_health != health[victim]
                        or b.attacker_focus != focus[holder] or b.attacker_rank != p.rank
                        or b.attacker_standard is not False or b.attacker_conscious is not (health[holder] > 0)
                        or b.attacker_stunned is not stunned[holder] or b.target_stunned is not stunned[victim]
                        or b.target_standard is not (timing == 'standard')
                        or b.target_reactions != ReactionPools(*old) or not b.grabbed
                        or b.pinned is not pinned or b.distance != 1):
                    issues.append(f'event {seq}: escape state does not match combat')
                issues.extend(audit_escape(tx, melee=q.melee, mighty=q.melee_bonus if 'mighty' in q.powers else 0,
                    grabber_melee_defense=p.melee_defense, timing=timing, trigger=trigger))
                if tx.success:
                    holder, victim, pinned = None, None, False
                escape_opportunity = None
                if timing == 'standard':
                    event = {'type': 'wait', 'actor': actor, 'round': event['round'],
                             'bonus_round': event['bonus_round'], 'rules': ['CORE-P30-ESCAPE']}
                else:
                    pending_reaction = None
                    continue
            except (KeyError, TypeError, ValueError, AttributeError) as error:
                issues.append(f'event {seq}: malformed escape transaction: {error}')
        elif kind == 'grapple_release':
            if actor != holder or holder is None or actor != active:
                issues.append(f'event {seq}: invalid voluntary release')
            holder, victim, pinned = None, None, False
            continue
        copy = dict(event)
        copy['seq'] = len(projection) + 1
        projection.append(copy)
    if pending is not None or pending_reaction is not None:
        issues.append('Unfinished grappling transaction')
    if issues:
        return issues
    return audit_declared_armed_melee(replace(result, log=tuple(projection)), profiles,
        declared_armed_lethal=declared_armed_lethal, allow_experimental_grappling=True, **context)
