"""Independent Focus ledger plus existing physical/Fast audits for a mixed duel."""

from dataclasses import replace

from blacklight.audit import audit_profiled_log
from blacklight.dice_audit import audit_rerolls
from blacklight.spatial_audit import audit_open_field_distance
from blacklight.turn_audit import audit_turn_sequence


def audit_mental_punch_split(result, profiles, *, expected_seed, max_rounds, initial_distance, ruleset):
    profiles = tuple(profiles)
    names = {p.name: p for p in profiles}
    if len(profiles) != 2 or len(names) != 2 or type(expected_seed) is not int or type(max_rounds) is not int:
        raise ValueError('Two distinct profiles and explicit result settings are required')
    if not isinstance(result.log, (list, tuple)) or any(not isinstance(e, dict) for e in result.log):
        return ['Invalid mixed-duel log']
    health = {p.name: p.max_health for p in profiles}
    focus = {p.name: p.max_focus for p in profiles}
    mental_loss = dict.fromkeys(names, 0)
    dodging = dict.fromkeys(names, False)
    stunned = dict.fromkeys(names, False)
    stun_expiry = {}
    turn_counts = dict.fromkeys(names, 0)
    prepared = {}
    counts = {p.name: dict.fromkeys(('damage_dealt', 'damage_taken', 'damage_mitigated',
        'healing_effective', 'focus_spent', 'attacks', 'hits', 'fantastic_hits', 'ripostes',
        'stuns_applied', 'blade_bonus_actions', 'damage_round3', 'damage_round5', 'damage_round10'), 0)
        for p in profiles}
    projection, issues = [], []
    pending_stun, mental_triggers = None, {}
    turns, rounds, bonus = 0, 0, False
    for index, event in enumerate(result.log):
        kind, actor, target, seq = (event.get('type'), event.get('actor'),
                                     event.get('target'), event.get('seq'))
        if type(seq) is not int or seq != index + 1:
            issues.append(f'event {seq}: invalid original sequence')
        round_number = event.get('round')
        if type(round_number) is not int or type(event.get('bonus_round')) is not bool:
            issues.append(f'event {seq}: invalid phase')
            continue
        rounds = max(rounds, round_number)
        if kind == 'initiative' and event.get('fantastic') is True:
            bonus = True
        if kind == 'turn_start':
            turns += 1
            if actor in turn_counts:
                if any(source == actor and deadline <= turn_counts[actor] + 1
                       for source, deadline in stun_expiry.values()):
                    issues.append(f'event {seq}: Stunned did not expire at its source turn')
                turn_counts[actor] += 1
                if stunned[actor]:
                    following = result.log[index + 1] if index + 1 < len(result.log) else {}
                    if following.get('type') != 'turn_skipped' or following.get('actor') != actor:
                        issues.append(f'event {seq}: stunned actor did not skip its turn')
        elif kind == 'turn_skipped' and (actor not in stunned or not stunned[actor]):
            issues.append(f'event {seq}: turn skipped without Stunned')
        if (actor in names and focus[actor] <= -names[actor].max_focus
                and kind in ('turn_start', 'attack', 'mental_attack', 'movement', 'reaction_spent',
                             'shield_activate', 'focus_spent', 'fast_use_start', 'dodge', 'wait')):
            issues.append(f'event {seq}: shattered actor took an action')
        if (actor in stunned and stunned[actor] and kind in
                ('attack', 'mental_attack', 'movement', 'reaction_spent', 'shield_activate',
                 'focus_spent', 'fast_use_start', 'dodge', 'wait', 'stance', 'condition_treatment')):
            issues.append(f'event {seq}: stunned actor took an action')
        if pending_stun is not None:
            if (kind != 'condition_start' or actor != pending_stun[0]
                    or event.get('condition') != 'stunned' or event.get('expires_on_actor') != pending_stun[1]
                    or 'CORE-P108-MENTAL-PUNCH' not in event.get('rules', ())):
                issues.append(f'event {seq}: missing Mental Punch Stunned effect')
            pending_stun = None
        if kind == 'dodge' and actor in dodging:
            dodging[actor] = True
        elif kind == 'dodge_end' and actor in dodging:
            dodging[actor] = False
        elif kind == 'condition_start' and actor in stunned and event.get('condition') == 'stunned':
            source, deadline = event.get('expires_on_actor'), event.get('source_turn_count')
            if (source not in names or type(deadline) is not int or deadline != turn_counts[source] + 1):
                issues.append(f'event {seq}: invalid Stunned duration')
            else:
                stun_expiry[actor] = (source, deadline)
            stunned[actor] = True
            if event.get('expires_on_actor') in counts:
                counts[event['expires_on_actor']]['stuns_applied'] += 1
        elif kind == 'condition_end' and actor in stunned and event.get('condition') == 'stunned':
            source_deadline = stun_expiry.get(actor)
            if (not stunned[actor] or source_deadline is None
                    or source_deadline[1] != turn_counts[source_deadline[0]] + 1):
                issues.append(f'event {seq}: invalid Stunned expiration')
            stun_expiry.pop(actor, None)
            stunned[actor] = False
        if kind == 'fast_limb_check' and actor in names and target in names:
            trigger = event.get('trigger')
            expected_trouble = int(focus[actor] <= 0) + int(dodging[target])
            edges = int('blazing_fast_fists' in names[actor].powers) + int('signature_fast_strikes' in names[actor].traits)
            if stunned[target]:
                edges = max(edges, 1)
            if (type(trigger) is not int or trigger in prepared or event.get('troubles') != expected_trouble
                    or event.get('edges') != edges):
                issues.append(f'event {seq}: Fast edge or trouble differs from profile and conditions')
            prepared[trigger] = expected_trouble
        if kind == 'mental_attack':
            p, q = names.get(actor), names.get(target)
            if (p is None or q is None or actor == target or 'mental_punch' not in p.powers
                    or p.melee_bonus != 0 or p.weapons or p.ranged_range or 'mighty' in p.powers
                    or 'attack_stance' in p.powers or event.get('distance') != 1
                    or type(event.get('trigger')) is not int or event['trigger'] in mental_triggers
                    or event.get('modifier') != p.melee or event.get('target_number') != q.melee_defense
                    or event.get('focus_reduction') != 0):
                issues.append(f'event {seq}: invalid Mental Punch source or target')
                continue
            mental_triggers[event['trigger']] = (actor, target, event.get('success'))
            roll, faces = event.get('roll'), event.get('damage_faces')
            if (not isinstance(roll, list) or len(roll) != 3 or any(type(x) is not int or not 1 <= x <= 6 for x in roll)
                    or not isinstance(faces, list) or any(type(x) is not int or not 1 <= x <= 6 for x in faces)):
                issues.append(f'event {seq}: invalid mental dice')
                continue
            edges = int('blazing_fast_fists' in p.powers)
            if stunned[q.name]:
                edges = max(edges, 1)
            troubles = int(focus[p.name] <= 0) + int(dodging[q.name])
            if event.get('edges') != edges or event.get('troubles') != troubles:
                issues.append(f'event {seq}: mental check edge or trouble mismatch')
            issues.extend(audit_rerolls(event, edges=edges, troubles=troubles))
            left, marvel, right = roll
            total = left + (6 if marvel == 1 else marvel) + right + p.melee
            ultimate = roll == [6, 1, 6]
            success, fantastic = ultimate or total >= q.melee_defense, marvel == 1
            if (event.get('total') != total or event.get('success') is not success
                    or event.get('fantastic') is not fantastic or event.get('ultimate') is not ultimate
                    or len(faces) != (p.rank if success else 0)):
                issues.append(f'event {seq}: mental check or damage pool mismatch')
            damage = max(0, sum(6 if face == 1 else face for face in faces) + p.melee) if success else 0
            if success and fantastic:
                damage *= 2
            before = focus[q.name]
            after = before - damage
            if p.heroic and after <= -q.max_focus:
                after = -q.max_focus + 1
            if (event.get('focus_before') != before or event.get('focus_after') != after
                    or event.get('calculated_damage') != damage or event.get('damage') != before - after
                    or event.get('demoralized') is not (after <= 0)
                    or event.get('shattered') is not (after <= -q.max_focus)):
                issues.append(f'event {seq}: mental Focus damage mismatch')
            focus[q.name] = after
            mental_loss[q.name] += before - after
            counts[p.name]['attacks'] += 1
            counts[p.name]['hits'] += int(success)
            counts[p.name]['fantastic_hits'] += int(success and fantastic)
            if success and fantastic and after > -q.max_focus:
                pending_stun = (q.name, p.name)
            if not success:
                following = result.log[index + 1] if index + 1 < len(result.log) else {}
                if (following.get('type') != 'reaction_queued' or following.get('actor') != q.name
                        or following.get('source') != p.name or following.get('trigger') != event['trigger']):
                    issues.append(f'event {seq}: missing mental miss reaction trigger')
            event = {'type': 'wait', 'actor': actor, 'round': round_number,
                     'bonus_round': event['bonus_round'], 'rules': ['CORE-P108-MENTAL-PUNCH']}
        elif kind == 'reaction_queued' and event.get('trigger') in mental_triggers:
            source, defender, success = mental_triggers[event['trigger']]
            if success or actor != defender or event.get('source') != source:
                issues.append(f'event {seq}: invalid mental miss reaction trigger')
        elif kind == 'reaction_spent' and event.get('trigger') in mental_triggers and 'POW-06' in event.get('rules', ()):
            source, defender, success = mental_triggers[event['trigger']]
            if success or actor != defender:
                issues.append(f'event {seq}: invalid mental miss Riposte')
        elif kind == 'attack' and actor in counts and target in counts:
            trigger = event.get('trigger')
            expected_trouble = prepared.get(trigger, int(focus[actor] <= 0) + int(dodging[target]))
            if event.get('troubles') != expected_trouble:
                issues.append(f'event {seq}: physical attack trouble differs from Focus and Dodge')
            damage = event['damage']
            counts[actor]['damage_dealt'] += damage
            counts[target]['damage_taken'] += damage
            counts[actor]['attacks'] += 1
            counts[actor]['hits'] += int(event['success'])
            counts[actor]['fantastic_hits'] += int(event['success'] and event['fantastic'])
            counts[actor]['ripostes'] += int(event['reaction'])
            for horizon in (3, 5, 10):
                if round_number <= horizon:
                    counts[actor][f'damage_round{horizon}'] += damage
            raw = sum(c.get('damage_without_reduction') or 0 for c in event.get('damage_components', ()))
            counts[target]['damage_mitigated'] += max(0, raw - event['calculated_damage'])
            health[target] = event['health_after']
        elif kind == 'heal' and actor in counts:
            counts[actor]['healing_effective'] += event['effective']
            health[actor] = event['health_after']
        elif kind == 'condition_tick' and actor in counts:
            counts[actor]['damage_taken'] += event['damage']
            health[actor] = event['health_after']
        elif kind == 'focus_spent' and actor in focus:
            amount = event.get('amount')
            if (event.get('focus_before') != focus[actor] or type(amount) is not int
                    or not 0 < amount <= 5 * names[actor].rank
                    or event.get('focus_after') != focus[actor] - amount or event['focus_after'] < 1):
                issues.append(f'event {seq}: mixed Focus spending mismatch')
            focus[actor] = event['focus_after']
            counts[actor]['focus_spent'] += event['amount']
            event = dict(event, focus_before=event['focus_before'] + mental_loss[actor],
                         focus_after=event['focus_after'] + mental_loss[actor])
        elif kind == 'turn_end' and actor in focus:
            if event.get('health') != health[actor] or event.get('focus') != focus[actor]:
                issues.append(f'event {seq}: mixed end-turn resource mismatch')
            event = dict(event, focus=event['focus'] + mental_loss[actor])
        elif kind == 'blade_bonus' and actor in counts:
            counts[actor]['blade_bonus_actions'] += 1
        copy = dict(event)
        copy['seq'] = len(projection) + 1
        projection.append(copy)
    if pending_stun:
        issues.append('Mental Punch Stunned effect missing at end of log')
    if (result.seed != expected_seed or tuple(result.final_health) != tuple(health[p.name] for p in profiles)
            or tuple(result.final_focus) != tuple(focus[p.name] for p in profiles)
            or result.rounds != rounds or result.turns != turns or result.bonus_round_occurred is not bonus):
        issues.append('Mixed duel summary mismatch')
    active = [p.name for p in profiles if health[p.name] > 0 and focus[p.name] > -p.max_focus]
    expected = ('inconclusive', None) if len(active) == 2 else ('win', active[0]) if active else ('draw', None)
    if (result.outcome, result.winner) != expected or len(active) == 2 and rounds != max_rounds:
        issues.append('Mixed duel outcome mismatch')
    if len(result.metrics) != 2:
        issues.append('Mixed duel metrics missing')
    else:
        for p, actual in zip(profiles, result.metrics):
            if actual != counts[p.name]:
                issues.append(f'Mixed duel metrics mismatch for {p.name}')
    try:
        issues.extend(audit_profiled_log(projection, profiles, ruleset=ruleset))
        issues.extend(audit_turn_sequence(projection, profiles, outcome=result.outcome))
        issues.extend(audit_open_field_distance(projection, initial_distance))
    except (KeyError, TypeError, ValueError, IndexError) as error:
        issues.append(f'Invalid mixed-duel projection: {error}')
    return issues
