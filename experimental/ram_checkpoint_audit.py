"""Independent audit of one stopped experimental bare-Ram duel checkpoint."""

from blacklight.audit import audit_profiled_log
from blacklight.spatial_audit import audit_open_field_distance
from .ram_opportunity_audit import audit_ram_opportunities
from .ram_rolled import audit_rolled_table_ram


def audit_ram_checkpoint(log, profiles, *, initial_distance, ruleset, seed):
    """Validate pre-checkpoint duel and Ram transaction; not a full-duel audit."""
    profiles = tuple(profiles)
    if len(profiles) != 2 or profiles[0].name == profiles[1].name:
        raise ValueError('Exactly two distinct profiles are required')
    if type(seed) is not int:
        raise ValueError('An integer seed is required for provenance')
    if (not isinstance(log, (tuple, list)) or not log
            or any(not isinstance(event, dict) for event in log)
            or log[-1].get('type') != 'ram_checkpoint_resolved'):
        return ['Missing terminal Ram checkpoint']
    prior, event = log[:-1], log[-1]
    issues = audit_profiled_log(prior, profiles, ruleset=ruleset)
    issues.extend(audit_open_field_distance(prior, initial_distance))
    issues.extend(audit_ram_opportunities(prior, profiles))
    if (not prior or prior[-1].get('type') != 'ram_opportunity'
            or type(event.get('seq')) is not int or type(prior[-1].get('seq')) is not int
            or event['seq'] != prior[-1]['seq'] + 1
            or event.get('round') != prior[-1].get('round')
            or event.get('bonus_round') != prior[-1].get('bonus_round')
            or event.get('rules') != ['ACT-01', 'ACT-03']
            or event.get('scope') != 'experimental bare Ram; combat stops immediately'):
        return issues + ['Ram checkpoint is not immediately after an opportunity']
    marker = prior[-1]
    names = {profile.name: profile for profile in profiles}
    actor, target = event.get('actor'), event.get('target')
    if actor not in names or target not in names or actor == target or (actor, target) != (marker.get('actor'), marker.get('target')):
        return issues + ['Ram checkpoint actor or target mismatch']
    record = event.get('transaction')
    transaction_issues = audit_rolled_table_ram(record)
    if transaction_issues:
        return issues + transaction_issues
    health = {p.name: p.max_health for p in profiles}
    reactions = {p.name: None for p in profiles}
    shield = {p.name: p.shield_active for p in profiles}
    stance = {p.name: False for p in profiles}
    stunned = {p.name: False for p in profiles}
    dodging = {p.name: False for p in profiles}
    turns = {p.name: 0 for p in profiles}
    for item in prior:
        kind, name = item.get('type'), item.get('actor')
        if name not in names:
            continue
        if kind in ('reaction_reset', 'turn_start'):
            reactions[name] = item.get('reactions')
        elif kind == 'reaction_spent':
            reactions[name] = item.get('remaining')
        if kind == 'turn_start':
            turns[name] += 1
        if kind == 'attack' and item.get('target') in names:
            health[item['target']] = item.get('health_after')
        elif kind in ('heal', 'condition_tick'):
            health[name] = item.get('health_after')
        if kind == 'shield_activate':
            shield[name] = True
        elif kind == 'shield_deactivate':
            shield[name] = False
        elif kind == 'stance':
            stance[name] = True
        elif kind == 'dodge':
            dodging[name] = True
        elif kind == 'dodge_end':
            dodging[name] = False
        elif kind == 'condition_start' and item.get('condition') == 'stunned':
            stunned[name] = True
            stance[name] = False
        elif kind == 'condition_end' and item.get('condition') == 'stunned':
            stunned[name] = False
        elif kind == 'knockback' and item.get('target') in stance:
            stance[item['target']] = False
    p, q = names[actor], names[target]
    supported_powers = {'healing_factor', 'brawling', 'fast_strikes', 'attack_stance',
                        'riposte', 'do_this_all_day', 'blazing_fast_fists',
                        'mighty', 'sturdy', 'accuracy'}
    supported_traits = {'battle_ready', 'combat_reflexes', 'situational_awareness',
                        'signature_fast_strikes'}
    supported_weapons = {'blade', 'claw', 'hammer', 'shield'}
    if any(profile.powers - supported_powers or profile.traits - supported_traits
           or profile.weapons - supported_weapons for profile in profiles):
        issues.append('A profile contains unsupported mechanics')
    before, params, check = record['before'], record['parameters'], record['check']
    if check['seed'] != seed:
        issues.append('Ram checkpoint seed does not match declared provenance')
    if (before != {'attacker_health': health[actor], 'target_health': health[target],
                   'reactions': reactions[actor], 'attacker_able': True, 'target_prone': False}
            or shield[actor] or shield[target] or stance[actor] or stunned[actor]
            or stunned[target] or dodging[target]
            or 'shield' in q.weapons and reactions[target] and reactions[target] > 0
            or 'riposte' in q.powers and reactions[target] and reactions[target] > 0):
        issues.append('Ram checkpoint state or unsupported interaction mismatch')
    if (params['full_dice'] != p.rank + max(0, p.melee_bonus) or params['ability'] != p.melee
            or params['target_reduction'] != q.health_dr or params['attacker_reduction'] != p.health_dr
            or check['modifier'] != p.melee or check['target_number'] != q.melee_defense
            or check['edges'] != int('blazing_fast_fists' in p.powers) or check['troubles'] != 0):
        issues.append('Ram checkpoint profile or check facts mismatch')
    first, second = record['first'], record['second']
    if (first['actor'] != actor or first['target'] != target or first['turn'] != turns[actor]
            or first['before'] != marker['first_before'] or first['after'] != marker['first_after']
            or second['after'] != marker['second_after'] or first['speed'] != p.run_speed):
        issues.append('Ram checkpoint movement evidence mismatch')
    if record['after']['target_health'] <= -q.max_health:
        issues.append('Unsupported nonlethal floor')
    return issues
