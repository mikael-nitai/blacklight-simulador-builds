"""Independent audit for experimental duels combining bare Ram and Prone."""

from dataclasses import replace

from blacklight.audit import audit_profiled_log
from blacklight.result_audit import audit_battle_result
from blacklight.spatial_audit import audit_open_field_distance
from .incapacity_endturn_audit import audit_incapacity_endturn
from .prone_duel_audit import audit_prone_log
from .ram_opportunity_audit import audit_ram_opportunities
from .ram_rolled import audit_rolled_table_ram


def _physical_projection(result, profiles):
    """Project verified Ram impacts to Health-only ticks for existing ledgers.

    This temporary projection is audit input, never the original trace. Ram
    arithmetic and profile facts must be checked separately before trusting it.
    """
    metrics = [dict(row) for row in result.metrics]
    positions = {profile.name: index for index, profile in enumerate(profiles)}
    projected = []
    for event in result.log:
        if event.get('type') != 'ram_attack':
            projected.append(dict(event))
            continue
        actor, target = event['actor'], event['target']
        record = event['transaction']
        impact, before, after = record['impact'], record['before'], record['after']
        actor_metrics, target_metrics = metrics[positions[actor]], metrics[positions[target]]
        actor_metrics['damage_dealt'] -= event['target_damage_applied']
        actor_metrics['attacks'] -= 1
        actor_metrics['hits'] -= int(record['parameters']['success'])
        actor_metrics['fantastic_hits'] -= int(record['parameters']['fantastic_success'])
        target_metrics['damage_mitigated'] -= event['target_damage_mitigated']
        for horizon in (3, 5, 10):
            if event['round'] <= horizon:
                actor_metrics[f'damage_round{horizon}'] -= event['target_damage_applied']
        for name, old, new, damage in (
                (target, before['target_health'], event['target_health_after'], event['target_damage_applied']),
                (actor, before['attacker_health'], event.get('attacker_health_after', after['attacker_health']),
                 event['attacker_damage_applied'])):
            projected.append({'type': 'condition_tick', 'actor': name, 'round': event['round'],
                              'bonus_round': event['bonus_round'], 'rules': ['ACT-05'],
                              'condition': 'ram_audit_projection', 'intensity': damage,
                              'damage': damage, 'health_before': old, 'health_after': new})
    for index, event in enumerate(projected, 1):
        event['seq'] = index
    return replace(result, log=tuple(projected), metrics=tuple(metrics))


def audit_ram_prone_duel(result, profiles, *, initial_prone, initial_distance,
                         expected_seed, max_rounds, ruleset, stack_stunned_edge=False,
                         self_damage_mode='reject_incapacitation', end_turn_healing_first=True):
    """Audit the full experimental result; never certify unsupported mechanics."""
    profiles = tuple(profiles)
    if len(profiles) != 2 or profiles[0].name == profiles[1].name:
        raise ValueError('Exactly two distinct profiles are required')
    if self_damage_mode not in ('reject_incapacitation', 'lethal_impact', 'nonlethal_impact'):
        raise ValueError('Unknown self-damage hypothesis')
    if type(end_turn_healing_first) is not bool:
        raise ValueError('Declare the end-turn healing order')
    names = {p.name: p for p in profiles}
    if not isinstance(result.log, (tuple, list)) or any(not isinstance(e, dict) for e in result.log):
        return ['Invalid experimental duel log']
    allowed = {'initiative', 'reaction_reset', 'turn_start', 'turn_end', 'turn_skipped',
               'movement', 'attack', 'fast_use_start', 'fast_limb_check', 'fast_limb_start',
               'fast_use_end', 'blade_bonus', 'stance', 'dodge', 'dodge_end', 'focus_spent',
               'wait', 'condition_treatment', 'condition_start', 'condition_end', 'condition_tick',
               'shield_activate', 'shield_deactivate', 'reaction_spent', 'reaction_queued',
               'heal', 'knockback', 'knockback_declined', 'limb_effect', 'prone_initial',
               'prone_stand', 'prone_check', 'prone_start', 'ram_opportunity', 'ram_declined',
               'ram_attack', 'incapacity_dead', 'incapacity_contract'}
    if (type(expected_seed) is not int or type(max_rounds) is not int or max_rounds < 1
            or type(result.rounds) is not int or type(result.turns) is not int
            or type(result.bonus_round_occurred) is not bool
            or any(not isinstance(v, tuple) or len(v) != 2 or any(type(x) is not int for x in v)
                   for v in (result.final_health, result.final_focus))
            or any(type(event.get('seq')) is not int or event['seq'] != index
            or type(event.get('round')) is not int or type(event.get('bonus_round')) is not bool
            or not isinstance(event.get('type'), str) or event['type'] not in allowed
            or event.get('actor') is not None and not isinstance(event['actor'], str)
            or event.get('target') is not None and not isinstance(event['target'], str)
            for index, event in enumerate(result.log, 1))
            or type(result.seed) is not int or not isinstance(result.metrics, tuple)
            or len(result.metrics) != 2 or any(not isinstance(row, dict)
                or any(type(value) is not int for value in row.values()) for row in result.metrics)):
        return ['Invalid experimental event sequence or metric types']
    issues = audit_prone_log(result.log, profiles, initial_prone=initial_prone,
                             initial_distance=initial_distance, stack_stunned_edge=stack_stunned_edge)
    issues += audit_ram_opportunities(result.log, profiles)
    if self_damage_mode != 'reject_incapacitation':
        try:
            issues += audit_incapacity_endturn(result.log, profiles, healing_first=end_turn_healing_first,
                                               self_damage_mode=self_damage_mode)
        except (KeyError, TypeError, ValueError, IndexError) as error:
            issues.append(f'Invalid experimental end-turn ledger: {error}')
    contracts = [(index, event) for index, event in enumerate(result.log)
                 if event.get('type') == 'incapacity_contract']
    if self_damage_mode == 'reject_incapacitation':
        if contracts:
            issues.append('Unexpected self-incapacity contract')
    elif (len(contracts) != 1 or contracts[0][0] != sum(initial_prone)
          or contracts[0][1].get('mode') != self_damage_mode
          or contracts[0][1].get('simultaneous') is not True
          or contracts[0][1].get('heal_living_at_turn_end') is not True
          or contracts[0][1].get('healing_first') is not end_turn_healing_first):
        issues.append('Missing or invalid self-incapacity contract')
    health = {p.name: p.max_health for p in profiles}
    reactions = {p.name: None for p in profiles}
    shield = {p.name: p.shield_active for p in profiles}
    stance = dict.fromkeys(names, False)
    stunned = dict.fromkeys(names, False)
    dodging = dict.fromkeys(names, False)
    prone = {p.name: value for p, value in zip(profiles, initial_prone)}
    turns = dict.fromkeys(names, 0)
    opportunity, pending, expect_queue, dead_end = None, None, None, None
    for event in result.log:
        kind, actor, target, seq = (event.get('type'), event.get('actor'),
                                     event.get('target'), event.get('seq'))
        started_ram = False
        if dead_end is not None:
            if kind != 'turn_end' or actor != dead_end:
                issues.append(f'event {seq}: dead actor must end the turn without effects')
            dead_end = None
        if expect_queue is not None:
            if (kind != 'reaction_queued' or (actor, event.get('source'), event.get('trigger')) != expect_queue):
                issues.append(f'event {seq}: missing Ram miss/Riposte queue')
            expect_queue = None
        if opportunity is not None:
            if kind == 'ram_declined' and (actor, target) == (opportunity['actor'], opportunity['target']):
                opportunity = None
                continue
            if kind == 'reaction_spent' and actor == opportunity['actor'] and event.get('source') == 'ram':
                pending = {'marker': opportunity, 'reactions_before': reactions.get(actor),
                           'shield_events': [], 'await_shield': False}
                started_ram = True
                opportunity = None
            else:
                issues.append(f'event {seq}: Ram opportunity lacks immediate policy decision')
                opportunity = None
        if kind == 'ram_opportunity':
            if pending is not None:
                issues.append(f'event {seq}: nested Ram opportunity')
            opportunity = event
            continue
        if kind == 'ram_declined':
            issues.append(f'event {seq}: unexpected Ram decline')
            continue
        if kind == 'reaction_spent' and event.get('source') == 'ram' and pending is None:
            issues.append(f'event {seq}: Ram reaction has no opportunity')
        if pending is not None and kind not in ('reaction_spent', 'prone_check', 'shield_activate', 'ram_attack'):
            issues.append(f'event {seq}: unexpected event while resolving Ram')
        if pending is not None and pending['await_shield']:
            if kind != 'shield_activate' or actor != pending['marker']['target']:
                issues.append(f'event {seq}: Ram Shield reaction was not activated immediately')
            pending['await_shield'] = False
        if pending is not None and kind == 'reaction_spent' and not started_ram:
            if actor != pending['marker']['target'] or type(event.get('trigger')) is not int:
                issues.append(f'event {seq}: unsupported reaction during Ram')
            pending['await_shield'] = True
        if actor not in names:
            if kind == 'ram_attack':
                issues.append(f'event {seq}: unknown Ram actor')
            continue
        if kind in ('reaction_reset', 'turn_start'):
            reactions[actor] = event.get('reactions')
        elif kind == 'reaction_spent':
            reactions[actor] = event.get('remaining')
        if kind == 'turn_start':
            turns[actor] += 1
        if (self_damage_mode != 'reject_incapacitation' and kind in ('heal', 'condition_tick')
                and type(health[actor]) is int and health[actor] <= -names[actor].max_health):
            issues.append(f'event {seq}: dead actor received an automatic end-turn effect')
        if self_damage_mode == 'reject_incapacitation' and kind == 'incapacity_dead':
            issues.append(f'event {seq}: death marker requires an explicit hypothesis')
        if self_damage_mode != 'reject_incapacitation' and kind == 'incapacity_dead':
            if (type(health[actor]) is not int or health[actor] > -names[actor].max_health
                    or type(event.get('health')) is not int or event['health'] != health[actor]
                    or event.get('mode') != self_damage_mode):
                issues.append(f'event {seq}: invalid death boundary')
            dead_end = actor
        if (self_damage_mode != 'reject_incapacitation' and kind == 'turn_end'
                and type(health[actor]) is int and health[actor] <= -names[actor].max_health
                and (result.log[event['seq'] - 2].get('type') != 'incapacity_dead'
                     or result.log[event['seq'] - 2].get('actor') != actor)):
            issues.append(f'event {seq}: dead actor ended turn without death marker')
        if kind == 'attack' and target in health:
            health[target] = event.get('health_after')
        elif kind in ('heal', 'condition_tick'):
            health[actor] = event.get('health_after')
        if kind == 'shield_activate':
            shield[actor] = True
            if pending is not None:
                pending['shield_events'].append(event)
        elif kind == 'shield_deactivate':
            shield[actor] = False
        elif kind == 'stance':
            stance[actor] = True
        elif kind == 'dodge':
            dodging[actor] = True
        elif kind == 'dodge_end':
            dodging[actor] = False
        elif kind == 'condition_start' and event.get('condition') == 'stunned':
            stunned[actor], stance[actor] = True, False
        elif kind == 'condition_end' and event.get('condition') == 'stunned':
            stunned[actor] = False
        elif kind == 'knockback' and target in stance:
            stance[target] = False
        elif kind == 'prone_stand':
            prone[actor] = False
        elif kind == 'prone_start':
            prone[actor] = True
        if kind != 'ram_attack':
            continue
        if (pending is None or target not in names or target == actor
                or (actor, target) != (pending['marker'].get('actor'), pending['marker'].get('target'))):
            issues.append(f'event {seq}: Ram has no matching opportunity and reaction')
            pending = None
            continue
        record = event.get('transaction')
        record_issues = audit_rolled_table_ram(record)
        if record_issues:
            issues += [f'event {seq}: {issue}' for issue in record_issues]
            pending = None
            continue
        p, q = names[actor], names[target]
        before, after, params, check, impact = (record[key] for key in
                                                 ('before', 'after', 'parameters', 'check', 'impact'))
        marker = pending['marker']
        first, second = record['first'], record['second']
        if (before != {'attacker_health': health[actor], 'target_health': health[target],
                       'reactions': pending['reactions_before'], 'attacker_able': True,
                       'target_prone': prone[target]}
                or reactions[actor] != before['reactions'] - 1 or shield[actor] or stance[actor]
                or stunned[actor] or not p.heroic and (p.weapons or p.ranged_range)
                or self_damage_mode == 'reject_incapacitation' and after['attacker_health'] <= 0
                or first['actor'] != actor or first['target'] != target or first['turn'] != turns[actor]
                or first['before'] != marker.get('first_before') or first['after'] != marker.get('first_after')
                or second['after'] != marker.get('second_after') or first['speed'] != p.run_speed):
            issues.append(f'event {seq}: Ram state or movement mismatch')
        base_edges = int('blazing_fast_fists' in p.powers)
        if stunned[target]:
            base_edges = base_edges + 1 if stack_stunned_edge else max(1, base_edges)
        expected_edges = base_edges + int(prone[target])
        expected_troubles = int(dodging[target]) + int(prone[actor])
        if (params['full_dice'] != p.rank + max(0, p.melee_bonus) or params['ability'] != p.melee
                or params['target_reduction'] != q.health_dr + (2 if shield[target] else 0)
                or params['attacker_reduction'] != p.health_dr or check['modifier'] != p.melee
                or check['target_number'] != q.melee_defense or check['edges'] != expected_edges
                or check['troubles'] != expected_troubles or check['seed'] != expected_seed
                or type(event.get('edges')) is not int or type(event.get('troubles')) is not int
                or event.get('edges') != expected_edges or event.get('troubles') != expected_troubles
                or event.get('mode') != 'melee' or type(event.get('trigger')) is not int):
            issues.append(f'event {seq}: Ram profile, check or reduction mismatch')
        if any(item.get('actor') != target or item.get('after_hit') is not True
               or item.get('trigger') != event.get('trigger') or not params['success']
               for item in pending['shield_events']):
            issues.append(f'event {seq}: invalid Shield reaction to Ram')
        # Bare Ram has no explicit lethal declaration in this host.
        final_target = max(-q.max_health + 1, after['target_health'])
        final_attacker = (max(-p.max_health + 1, after['attacker_health'])
                          if self_damage_mode == 'nonlethal_impact' else after['attacker_health'])
        applied = before['target_health'] - final_target
        self_applied = before['attacker_health'] - final_attacker
        faces = params['target_faces']
        raw = max(0, sum(6 if face == 1 else face for face in faces) + p.melee) if params['success'] and params['full_dice'] else 0
        raw *= 3 if params['fantastic_success'] else 2
        mitigation = max(0, raw - impact['target_damage'])
        expected_scope = ('experimental bare Ram; simultaneous damage; no self-incapacitation'
                          if self_damage_mode == 'reject_incapacitation' else
                          'experimental bare Ram; simultaneous damage; self-incapacity hypothesis')
        actor_after = event.get('attacker_health_after', after['attacker_health'])
        recorded_mode = event.get('self_damage_mode', 'reject_incapacitation')
        if (any(type(event.get(key)) is not int for key in
                ('target_health_after', 'target_damage_applied', 'attacker_damage_applied', 'target_damage_mitigated'))
                or type(actor_after) is not int or actor_after != final_attacker or recorded_mode != self_damage_mode
                or event.get('target_health_after') != final_target or event.get('target_damage_applied') != applied
                or event.get('attacker_damage_applied') != self_applied
                or event.get('target_damage_mitigated') != mitigation
                or event.get('scope') != expected_scope):
            issues.append(f'event {seq}: Ram applied damage or scope mismatch')
        health[actor], health[target] = final_attacker, final_target
        if final_target <= 0:
            stance[target] = False
        if not params['success']:
            expect_queue = (target, actor, event['trigger'])
        pending = None
    if opportunity is not None or pending is not None or expect_queue is not None or dead_end is not None:
        issues.append('Experimental duel ends with unresolved Ram event')
    if issues:
        return issues
    try:
        projection = _physical_projection(result, profiles)
        issues += audit_profiled_log(projection.log, profiles, ruleset=ruleset)
        issues += audit_battle_result(projection, profiles, expected_seed=expected_seed, max_rounds=max_rounds)
        issues += audit_open_field_distance(projection.log, initial_distance)
    except (KeyError, TypeError, ValueError, IndexError) as error:
        issues.append(f'Invalid experimental Ram audit projection: {error}')
    return issues
