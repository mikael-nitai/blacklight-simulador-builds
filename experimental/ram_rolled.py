"""Seeded experimental Ram transaction with d616 and separate damage pools."""

from dataclasses import asdict
from random import Random

from blacklight.dice import resolve_check
from blacklight.dice_audit import audit_rerolls
from .ram_record import record_table_ram
from .ram_record_audit import audit_table_ram_record
from .ram_transaction import execute_table_ram


def rolled_table_ram(state, first, second, *, seed, modifier, target_number,
                     full_dice, ability, target_reduction, attacker_reduction,
                     edges=0, troubles=0):
    """Resolve a synthetic check and separately rolled pools, with fixed seeds.

    This is not a combat host. It assumes no Shield, Heroic, Riposte, weapon
    effects, or intervening reactions, and records the impact model's simultaneous
    application hypothesis. Rolls contain full pools before the independent DRs.
    """
    if (any(type(value) is not int for value in (seed, modifier, target_number, edges, troubles))
            or edges < 0 or troubles < 0):
        raise ValueError('Invalid experimental Ram check')
    base = dict(full_dice=full_dice, ability=ability, target_reduction=target_reduction,
                attacker_reduction=attacker_reduction)
    # Check the entire reaction and parameter contract before sampling any dice.
    execute_table_ram(state, first, second, success=False, fantastic_success=False,
                      target_faces=(), attacker_faces=(), **base)
    hit_rng = Random(seed)
    damage_rng = Random(seed ^ 0xD6162026)
    result, rerolls = resolve_check(hit_rng, modifier, target_number, edges=edges, troubles=troubles)
    if result.success:
        target_faces = tuple(damage_rng.randint(1, 6) for _ in range(full_dice))
        attacker_faces = tuple(damage_rng.randint(1, 6) for _ in range(full_dice))
    else:
        target_faces = attacker_faces = ()
    record = record_table_ram(state, first, second, success=result.success,
                              fantastic_success=result.success and result.fantastic,
                              target_faces=target_faces, attacker_faces=attacker_faces, **base)
    record['check'] = {'seed': seed, 'roll': [result.roll.left, result.roll.marvel, result.roll.right],
                       'rerolls': [asdict(trace) for trace in rerolls], 'modifier': modifier,
                       'target_number': target_number, 'edges': edges, 'troubles': troubles,
                       'total': result.total, 'success': result.success,
                       'fantastic_roll': result.fantastic, 'ultimate': result.ultimate}
    return record


def audit_rolled_table_ram(record):
    """Check the ledger and table rule; this does not authenticate its seed."""
    issues = audit_table_ram_record(record)
    if issues:
        return issues
    check = record.get('check')
    if (not isinstance(check, dict) or any(type(check.get(k)) is not int for k in
            ('seed', 'modifier', 'target_number', 'edges', 'troubles', 'total'))
            or check['edges'] < 0 or check['troubles'] < 0
            or any(type(check.get(k)) is not bool for k in ('success', 'fantastic_roll', 'ultimate'))):
        return ['Invalid experimental Ram check record']
    issues = audit_rerolls(check, edges=check['edges'], troubles=check['troubles'])
    if issues:
        return issues
    left, marvel, right = check['roll']
    total = left + (6 if marvel == 1 else marvel) + right + check['modifier']
    ultimate = [left, marvel, right] == [6, 1, 6]
    success = ultimate or total >= check['target_number']
    if (check['total'] != total or check['ultimate'] != ultimate
            or check['fantastic_roll'] != (marvel == 1) or check['success'] != success
            or record['parameters']['success'] != success
            or record['parameters']['fantastic_success'] != (success and marvel == 1)):
        return ['Experimental Ram check result disagrees with recorded dice']
    return []
